"""Frozen gateway contract. Browser requests cannot carry actions or verdicts."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Decision = Literal["ALLOW", "REDACT", "BLOCK", "HOLD"]
RunStatus = Literal["RUNNING", "ALLOW", "REDACT", "BLOCK", "HOLD", "BASELINE"]

class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = Field(min_length=1, max_length=80)
    mode: Literal["baseline", "protected"] = "protected"

class Check(BaseModel):
    endpoint: Literal["injection", "pii", "script"]
    status: Literal["ok", "error"] = "ok"
    verdict: Optional[str] = None
    outcome: Optional[Decision] = None
    input_text: str
    safe_text: Optional[str] = None
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0
    model_ms: Optional[float] = None
    credits: Optional[float] = None
    cost_usd: Optional[float] = None
    cost_basis: Optional[str] = None
    error: Optional[str] = None

class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["read_document", "send_message", "propose_script", "record_action"]
    arguments: Dict[str, Any] = Field(default_factory=dict)

class Scenario(BaseModel):
    id: str
    title: str
    subtitle: str
    category: Literal["injection", "privacy", "script", "benign", "failure"]
    description: str
    task: str
    source_name: str
    content: str
    script: Optional[str] = None
    capabilities: List[str]
    proposed_action: Action
    baseline_consequence: str
    expected_protected: str
    endpoints: List[str]
    synthetic: bool = True

class TraceEvent(BaseModel):
    id: int
    run_id: str
    timestamp: str
    type: Literal["received", "check_started", "check_completed", "policy", "agent", "tool", "completed", "error", "review"]
    title: str
    detail: str
    data: Dict[str, Any] = Field(default_factory=dict)

class Run(BaseModel):
    run_id: str
    scenario_id: str
    mode: Literal["baseline", "protected"]
    status: RunStatus = "RUNNING"
    reason: str = "awaiting_security_checks"
    started_at: str
    completed_at: Optional[str] = None
    checks: List[Check] = Field(default_factory=list)
    events: List[TraceEvent] = Field(default_factory=list)
    action_executed: bool = False
    agent_input: Optional[str] = None
    proposed_action: Optional[Action] = None
    action_digest: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    baseline_label: Optional[str] = None
    latency_ms: Optional[float] = None
    credits: Optional[float] = None
    cost_usd: Optional[float] = None

class Metrics(BaseModel):
    runs: int = 0
    protected_runs: int = 0
    checks: int = 0
    blocked: int = 0
    held: int = 0
    allowed: int = 0
    redacted: int = 0
    avg_latency_ms: Optional[float] = None
    credits: Optional[float] = None
    cost_usd: Optional[float] = None

class ReviewResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "deny"]
    action_digest: str
    note: str = Field(default="", max_length=1000)
