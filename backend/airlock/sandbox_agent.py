"""A deterministic agent simulator, not an observed model jailbreak.

The protected path accepts only screened context and a server-owned action plan.
The simulator has no tool object, network client, original document or authority.
"""
from __future__ import annotations

from .models import Action


class SandboxAgent:
    def propose(self, agent_input: str, plan: Action) -> Action:
        if not isinstance(agent_input, str):
            raise ValueError("screened_context_required")
        # Copy the server-owned synthetic proposal so later mutation is detectable.
        # No content-derived instructions are interpreted or evaluated.
        return plan.model_copy(deep=True)
