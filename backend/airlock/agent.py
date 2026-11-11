"""Agent execution engine.

Processes screened context and prepares tool proposals for the Airlock gateway.
"""
from __future__ import annotations

from .models import Action


class Agent:
    def propose(self, agent_input: str, plan: Action) -> Action:
        if not isinstance(agent_input, str):
            raise ValueError("screened_context_required")
        return plan.model_copy(deep=True)


SandboxAgent = Agent
