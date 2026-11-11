"""Trusted orchestration: inspect, apply policy, then invoke a simulated tool."""
from __future__ import annotations

import asyncio
import hmac
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .agent import Agent
from .events import append_event, utc_now
from .models import Check, ReviewResolution, Run, Scenario
from .policy import POLICY_VERSION, action_digest, authorize_action, injection_decision, pii_decision, script_decision
from .real_tools import RealTools, ToolDenied
from .storage import Storage


def load_scenarios(directory: Optional[Path] = None) -> Dict[str, Scenario]:
    folder = directory or Path(__file__).resolve().parents[2] / "fixtures"
    scenarios = [Scenario.model_validate_json(path.read_text()) for path in sorted(folder.glob("*.json"))]
    return {scenario.id: scenario for scenario in scenarios}


class ReviewConflict(Exception):
    pass


class Gateway:
    def __init__(self, storage: Storage, adapter: Any, scenarios: Optional[Dict[str, Scenario]] = None, tools: Optional[RealTools] = None):
        self.storage = storage
        self.adapter = adapter
        self.scenarios = scenarios if scenarios is not None else load_scenarios()
        self.tools = tools if tools is not None else RealTools(storage=storage)
        self.agent = Agent()
        self._active = set()

    def create_run(self, scenario_id: str, mode: str = "protected") -> Run:
        if mode not in {"baseline", "protected"}:
            raise ValueError("unsupported_mode")
        scenario = self.scenarios[scenario_id]
        run = Run(run_id="run_" + uuid.uuid4().hex, scenario_id=scenario_id, mode=mode, started_at=utc_now(), action_digest=action_digest(scenario.proposed_action))
        append_event(run, "received", "External document received", scenario.source_name + " · live inspection", {"source_name": scenario.source_name, "input_text": scenario.content, "task": scenario.task, "policy_version": POLICY_VERSION})
        self.storage.save(run)
        return run

    def _event(self, run: Run, event_type: str, title: str, detail: str, data=None):
        append_event(run, event_type, title, detail, data)
        self.storage.save(run)

    def _finish(self, run: Run, status: str, reason: str, started: float) -> Run:
        run.status, run.reason = status, reason
        run.completed_at = utc_now()
        run.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        credits = [check.credits for check in run.checks if check.credits is not None]
        costs = [check.cost_usd for check in run.checks if check.cost_usd is not None]
        run.credits = sum(credits) if credits else None
        run.cost_usd = sum(costs) if costs else None
        self._event(run, "completed", "Run " + status.lower(), reason, {"status": status, "reason": reason, "action_executed": run.action_executed, "live_execution": True})
        return run

    async def _check(self, run: Run, adapter: Any, endpoint: str, text: str):
        method = {"injection": "check_injection", "pii": "redact_personal_data", "script": "inspect_script"}[endpoint]
        name = {"injection": "Guard", "pii": "Protect", "script": "Inspect"}[endpoint]
        self._event(run, "check_started", name + " screening", "Awaiting security classification.", {"endpoint": endpoint, "input_text": text})
        started = time.perf_counter()
        try:
            check = await getattr(adapter, method)(text)
            if not isinstance(check, Check) or check.endpoint != endpoint or check.input_text != text:
                check = Check(endpoint=endpoint, status="error", input_text=text, error="invalid_security_response", latency_ms=(time.perf_counter() - started) * 1000)
        except asyncio.CancelledError:
            raise
        except Exception:
            check = Check(endpoint=endpoint, status="error", input_text=text, error="security_check_unavailable", latency_ms=(time.perf_counter() - started) * 1000)
        decision, reason = {"injection": injection_decision, "pii": pii_decision, "script": script_decision}[endpoint](check)
        check.outcome = decision
        run.checks.append(check)
        self._event(run, "check_completed", name + " · " + decision, reason, {"endpoint": endpoint, "check": check.model_dump(mode="json"), "reason": reason})
        self._event(run, "policy", "Enforcement · " + decision, reason, {"endpoint": endpoint, "decision": decision, "policy_version": POLICY_VERSION})
        return check, decision, reason

    async def process(self, run_id: str) -> Run:
        run = self.storage.get(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status != "RUNNING" or run_id in self._active:
            return run
        self._active.add(run_id)
        started = time.perf_counter()
        try:
            scenario = self.scenarios[run.scenario_id]
            if not run.action_digest or not hmac.compare_digest(run.action_digest, action_digest(scenario.proposed_action)):
                return self._finish(run, "BLOCK", "action_changed_after_approval", started)
            if run.mode == "baseline":
                run.baseline_label = "Deterministic simulation — unshielded agent executed with no security screening."
                run.agent_input = scenario.content
                run.proposed_action = self.agent.propose(scenario.content, scenario.proposed_action)
                self._event(run, "agent", "Unprotected agent invoked", "Agent processed raw external input directly without security inspection.", {"agent_input": run.agent_input, "proposed_action": run.proposed_action.model_dump(mode="json")})
                if run.proposed_action.tool == "send_message" and hasattr(self.storage, "record_outbox_message"):
                    args = run.proposed_action.arguments
                    self.storage.record_outbox_message(run.run_id, "baseline", args.get("recipient", "audit-drop@example.invalid"), args.get("body", ""), blocked=False)
                elif run.proposed_action.tool == "record_action" and hasattr(self.storage, "record_support_ticket"):
                    self.storage.record_support_ticket(run.run_id, "baseline", "Maya Chen", "maya.chen@example.com", "+1 415-555-0138", "Office printer offline after update (Unredacted PII)", pii_scrubbed=False)
                run.tool_result = {"simulated": True, "executed": True, "security_bypassed": True, "effect": scenario.baseline_consequence, "tool": run.proposed_action.tool}
                run.action_executed = True
                self._event(run, "tool", "Unprotected action executed", scenario.baseline_consequence, run.tool_result)
                return self._finish(run, "BASELINE", "unprotected_baseline_execution", started)
            adapter = self.adapter
            if scenario.id == "security_unavailable":
                from .clocked_adapter import UnavailableAdapter
                adapter = UnavailableAdapter()
                self._event(run, "error", "Failure drill enabled", "The adapter is deliberately unavailable for this synthetic test; this is not an observed Clocked outage.", {"injected_failure": True})
            _, decision, reason = await self._check(run, adapter, "injection", scenario.content)
            if decision != "ALLOW":
                return self._finish(run, decision, reason, started)
            pii, decision, reason = await self._check(run, adapter, "pii", scenario.content)
            if decision not in {"ALLOW", "REDACT"}:
                return self._finish(run, decision, reason, started)
            was_redacted = decision == "REDACT"
            run.agent_input = pii.safe_text
            run.proposed_action = self.agent.propose(run.agent_input, scenario.proposed_action)
            self._event(run, "agent", "Screened context delivered", "Agent received only Clocked Protect's sanitized safe text.", {"agent_input": run.agent_input, "proposed_action": run.proposed_action.model_dump(mode="json")})
            if run.proposed_action.tool == "propose_script":
                script = run.proposed_action.arguments.get("script")
                if not isinstance(script, str):
                    return self._finish(run, "BLOCK", "invalid_tool_arguments", started)
                _, decision, reason = await self._check(run, adapter, "script", script)
                if decision != "ALLOW":
                    return self._finish(run, decision, reason, started)
            decision, reason = authorize_action(run.proposed_action, scenario.capabilities)
            self._event(run, "policy", "Tool authorization · " + decision, reason, {"decision": decision, "capabilities": scenario.capabilities, "action_digest": run.action_digest})
            if decision != "ALLOW":
                return self._finish(run, decision, reason, started)
            try:
                run.tool_result = self.tools.execute(
                    run.proposed_action,
                    approved_digest=run.action_digest,
                    capabilities=scenario.capabilities,
                    agent_input=run.agent_input,
                    run_id=run.run_id,
                    mode="protected",
                )
            except ToolDenied as denied:
                return self._finish(run, "BLOCK", str(denied), started)
            run.action_executed = True
            self._event(run, "tool", "Authorized action executed", run.tool_result.get("effect", "Action executed through gateway."), run.tool_result)
            return self._finish(run, "REDACT" if was_redacted else "ALLOW", "personal_data_redacted" if was_redacted else "authorized_action_executed", started)
        except asyncio.CancelledError:
            self._finish(run, "HOLD", "gateway_interrupted", started)
            raise
        except Exception:
            return self._finish(run, "HOLD", "security_check_unavailable", started)
        finally:
            self._active.discard(run_id)

    async def resolve_review(self, run_id: str, resolution: ReviewResolution) -> Run:
        run = self.storage.get(run_id)
        if run is None:
            raise KeyError(run_id)
        scenario = self.scenarios[run.scenario_id]
        digest = action_digest(scenario.proposed_action)
        if run.mode != "protected" or not run.action_digest or not hmac.compare_digest(run.action_digest, resolution.action_digest) or not hmac.compare_digest(digest, run.action_digest):
            raise ReviewConflict("action_digest_mismatch")
        if run.proposed_action and not hmac.compare_digest(action_digest(run.proposed_action), digest):
            raise ReviewConflict("action_changed_after_approval")
        if not self.storage.claim_review(run_id, resolution.decision):
            raise ReviewConflict("review_already_resolved_or_not_held")
        self._event(run, "review", "Reviewer decision: " + resolution.decision, "Authenticated reviewer channel; approval requests fresh checks and never bypasses them.", {"decision": resolution.decision, "note": resolution.note, "action_digest": digest, "revalidation_required": resolution.decision == "approve"})
        if resolution.decision == "deny":
            return self._finish(run, "BLOCK", "reviewer_denied", time.perf_counter())
        run.status, run.reason = "RUNNING", "review_revalidation"
        run.completed_at = None
        run.agent_input = None
        run.proposed_action = None
        run.tool_result = None
        run.action_executed = False
        self.storage.save(run)
        return await self.process(run_id)
