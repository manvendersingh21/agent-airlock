"""Audit events contain synthetic inputs and exact screening results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from .models import Run, TraceEvent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(run: Run, event_type: str, title: str, detail: str, data: Optional[Dict[str, Any]] = None) -> TraceEvent:
    event = TraceEvent(id=len(run.events) + 1, run_id=run.run_id, timestamp=utc_now(), type=event_type, title=title, detail=detail, data=data or {})
    run.events.append(event)
    return event
