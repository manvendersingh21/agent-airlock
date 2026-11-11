"""SQLite audit storage. Full snapshots make SSE replays survive connections."""
from __future__ import annotations

import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .events import append_event, utc_now
from .models import Metrics, Run


class Storage:
    def __init__(self, database_url: str = "sqlite:///./airlock.db"):
        path = database_url.removeprefix("sqlite:///")
        if path != ":memory:":
            try:
                Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                path = "/tmp/airlock.db"
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        try:
            self._connection = sqlite3.connect(path, check_same_thread=False, timeout=10)
        except sqlite3.OperationalError:
            path = "/tmp/airlock.db"
            self._connection = sqlite3.connect(path, check_same_thread=False, timeout=10)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=10000")
        self._connection.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, status TEXT NOT NULL, mode TEXT NOT NULL, data TEXT NOT NULL)")
        self._connection.execute("CREATE TABLE IF NOT EXISTS reviews (run_id TEXT PRIMARY KEY REFERENCES runs(run_id), decision TEXT NOT NULL, resolved_at TEXT NOT NULL)")
        self._connection.execute("CREATE TABLE IF NOT EXISTS outbox_messages (message_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, mode TEXT NOT NULL, recipient TEXT NOT NULL, body TEXT NOT NULL, sent_at TEXT NOT NULL, blocked INTEGER NOT NULL DEFAULT 0)")
        self._connection.execute("CREATE TABLE IF NOT EXISTS support_tickets (ticket_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, mode TEXT NOT NULL, customer_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL, issue_summary TEXT NOT NULL, created_at TEXT NOT NULL, pii_scrubbed INTEGER NOT NULL DEFAULT 0)")
        self._connection.commit()

    def save(self, run: Run) -> None:
        with self._lock, self._connection:
            self._connection.execute("INSERT INTO runs(run_id, started_at, status, mode, data) VALUES(?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, data=excluded.data", (run.run_id, run.started_at, run.status, run.mode, run.model_dump_json()))

    def get(self, run_id: str) -> Optional[Run]:
        with self._lock:
            row = self._connection.execute("SELECT data FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return Run.model_validate_json(row[0]) if row else None

    def list_runs(self, limit: int = 100) -> List[Run]:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM runs ORDER BY started_at DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()
        return [Run.model_validate_json(row[0]) for row in rows]

    def pending_reviews(self) -> List[Run]:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM runs WHERE status='HOLD' AND run_id NOT IN (SELECT run_id FROM reviews) ORDER BY started_at DESC LIMIT 100").fetchall()
        return [Run.model_validate_json(row[0]) for row in rows]

    def claim_review(self, run_id: str, decision: str) -> bool:
        with self._lock, self._connection:
            row = self._connection.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not row or row[0] != "HOLD":
                return False
            try:
                self._connection.execute("INSERT INTO reviews(run_id, decision, resolved_at) VALUES(?,?,?)", (run_id, decision, utc_now()))
            except sqlite3.IntegrityError:
                return False
        return True

    def recover_interrupted(self) -> int:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM runs WHERE status='RUNNING'").fetchall()
            for row in rows:
                run = Run.model_validate_json(row[0])
                run.status, run.reason = "HOLD", "gateway_restarted"
                run.completed_at = utc_now()
                append_event(run, "error", "Execution interrupted", "Gateway restarted before completion. No automatic retry or approval.", {"reason": run.reason})
                self.save(run)
        return len(rows)

    def metrics(self) -> Metrics:
        with self._lock:
            rows = self._connection.execute("SELECT data FROM runs").fetchall()
        runs = [Run.model_validate_json(row[0]) for row in rows]
        protected = [run for run in runs if run.mode == "protected"]
        checks = [check for run in protected for check in run.checks]
        successful = [check for check in checks if check.status == "ok"]
        credits = [check.credits for check in checks if check.credits is not None]
        costs = [check.cost_usd for check in checks if check.cost_usd is not None]
        return Metrics(runs=len(runs), protected_runs=len(protected), checks=len(checks), blocked=sum(run.status == "BLOCK" for run in protected), held=sum(run.status == "HOLD" for run in protected), allowed=sum(run.status == "ALLOW" for run in protected), redacted=sum(run.status == "REDACT" for run in protected), avg_latency_ms=(sum(check.latency_ms for check in successful) / len(successful)) if successful else None, credits=sum(credits) if credits else None, cost_usd=sum(costs) if costs else None)

    def record_outbox_message(self, run_id: str, mode: str, recipient: str, body: str, blocked: bool = False) -> Dict[str, Any]:
        msg_id = "msg_" + uuid.uuid4().hex[:10]
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO outbox_messages(message_id, run_id, mode, recipient, body, sent_at, blocked) VALUES(?,?,?,?,?,?,?)",
                (msg_id, run_id, mode, recipient, body, now, 1 if blocked else 0)
            )
        return {
            "message_id": msg_id,
            "run_id": run_id,
            "mode": mode,
            "recipient": recipient,
            "body": body,
            "sent_at": now,
            "blocked": blocked,
        }

    def list_outbox(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT message_id, run_id, mode, recipient, body, sent_at, blocked FROM outbox_messages ORDER BY sent_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {
                "message_id": r[0],
                "run_id": r[1],
                "mode": r[2],
                "recipient": r[3],
                "body": r[4],
                "sent_at": r[5],
                "blocked": bool(r[6]),
            }
            for r in rows
        ]

    def record_support_ticket(self, run_id: str, mode: str, customer_name: str, email: str, phone: str, issue_summary: str, pii_scrubbed: bool = False) -> Dict[str, Any]:
        t_id = "tkt_" + uuid.uuid4().hex[:10]
        now = utc_now()
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO support_tickets(ticket_id, run_id, mode, customer_name, email, phone, issue_summary, created_at, pii_scrubbed) VALUES(?,?,?,?,?,?,?,?,?)",
                (t_id, run_id, mode, customer_name, email, phone, issue_summary, now, 1 if pii_scrubbed else 0)
            )
        return {
            "ticket_id": t_id,
            "run_id": run_id,
            "mode": mode,
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "issue_summary": issue_summary,
            "created_at": now,
            "pii_scrubbed": pii_scrubbed,
        }

    def list_tickets(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT ticket_id, run_id, mode, customer_name, email, phone, issue_summary, created_at, pii_scrubbed FROM support_tickets ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [
            {
                "ticket_id": r[0],
                "run_id": r[1],
                "mode": r[2],
                "customer_name": r[3],
                "email": r[4],
                "phone": r[5],
                "issue_summary": r[6],
                "created_at": r[7],
                "pii_scrubbed": bool(r[8]),
            }
            for r in rows
        ]

    def clear_system_state(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM outbox_messages")
            self._connection.execute("DELETE FROM support_tickets")

    def close(self) -> None:
        with self._lock:
            self._connection.close()
