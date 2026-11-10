"""Allowlisted data transformations only. No shell or outbound messaging APIs."""
from __future__ import annotations

import hmac
from typing import Any, Dict, Iterable

from .models import Action
from .policy import action_digest, authorize_action


class ToolDenied(Exception):
    pass


class SimulatedTools:
    def __init__(self):
        self.invocations = 0

    def execute(self, action: Action, *, approved_digest: str, capabilities: Iterable[str], agent_input: str) -> Dict[str, Any]:
        if not approved_digest or not hmac.compare_digest(action_digest(action), approved_digest):
            raise ToolDenied("action_changed_after_approval")
        decision, reason = authorize_action(action, capabilities)
        if decision != "ALLOW":
            raise ToolDenied(reason)
        if not isinstance(agent_input, str):
            raise ToolDenied("screened_context_required")
        self.invocations += 1
        if action.tool == "propose_script":
            return {"simulated": True, "tool": action.tool, "script": action.arguments["script"], "effect": "Read-only diagnostic accepted; no process was started.", "context": agent_input}
        if action.tool == "read_document":
            return {"simulated": True, "tool": action.tool, "document": agent_input}
        return {"simulated": True, "tool": action.tool, "kind": action.arguments["kind"], "recorded_context": agent_input, "effect": "Recorded the screened context in this run only."}
