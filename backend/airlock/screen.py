"""Interactive multi-endpoint screening for Agent Airlock.

Allows arbitrary custom input to be inspected by Clocked Guard, Protect, and Inspect
with live visual diff calculation and policy evaluation.
"""
from __future__ import annotations

import difflib
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .clocked_adapter import ClockedAdapter
from .models import Check, Decision
from .policy import POLICY_VERSION, injection_decision, pii_decision, script_decision


class ScreenRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    script: Optional[str] = Field(default=None, max_length=10000)
    check_guard: bool = True
    check_protect: bool = True
    check_inspect: bool = True


class DiffToken(BaseModel):
    kind: str  # "equal", "deleted", "added"
    text: str


class ScreenResult(BaseModel):
    decision: Decision
    reason: str
    policy_version: str = POLICY_VERSION
    guard: Optional[Check] = None
    protect: Optional[Check] = None
    inspect: Optional[Check] = None
    redaction_diff: List[DiffToken] = Field(default_factory=list)
    entities_detected: List[Dict[str, Any]] = Field(default_factory=list)
    total_latency_ms: float = 0
    total_credits: float = 0
    total_cost_usd: float = 0


def compute_text_diff(original: str, modified: str) -> List[DiffToken]:
    """Compute word/token-level diff between original and redacted text."""
    matcher = difflib.SequenceMatcher(None, original.split(), modified.split())
    tokens: List[DiffToken] = []
    orig_words = original.split()
    mod_words = modified.split()
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            tokens.append(DiffToken(kind="equal", text=" ".join(orig_words[i1:i2])))
        elif tag == "delete":
            tokens.append(DiffToken(kind="deleted", text=" ".join(orig_words[i1:i2])))
        elif tag == "insert":
            tokens.append(DiffToken(kind="added", text=" ".join(mod_words[j1:j2])))
        elif tag == "replace":
            tokens.append(DiffToken(kind="deleted", text=" ".join(orig_words[i1:i2])))
            tokens.append(DiffToken(kind="added", text=" ".join(mod_words[j1:j2])))
    return tokens


async def screen_custom_input(adapter: Any, req: ScreenRequest) -> ScreenResult:
    started = time.perf_counter()
    overall_decision: Decision = "ALLOW"
    reasons: List[str] = []
    
    guard_check: Optional[Check] = None
    protect_check: Optional[Check] = None
    inspect_check: Optional[Check] = None
    
    # 1. Guard check (Prompt Injection)
    if req.check_guard and req.text:
        guard_check = await adapter.check_injection(req.text)
        dec, rsn = injection_decision(guard_check)
        guard_check.outcome = dec
        if dec == "BLOCK":
            overall_decision = "BLOCK"
            reasons.append(rsn)
        elif dec == "HOLD" and overall_decision != "BLOCK":
            overall_decision = "HOLD"
            reasons.append(rsn)

    # 2. Protect check (PII / Privacy)
    diff_tokens: List[DiffToken] = []
    entities: List[Dict[str, Any]] = []
    if req.check_protect and req.text and overall_decision != "BLOCK":
        protect_check = await adapter.redact_personal_data(req.text)
        dec, rsn = pii_decision(protect_check)
        protect_check.outcome = dec
        if dec == "REDACT" and overall_decision == "ALLOW":
            overall_decision = "REDACT"
            reasons.append(rsn)
        elif dec in {"BLOCK", "HOLD"} and overall_decision != "BLOCK":
            overall_decision = dec
            reasons.append(rsn)
            
        if protect_check.safe_text and protect_check.safe_text != req.text:
            diff_tokens = compute_text_diff(req.text, protect_check.safe_text)
            raw_entities = protect_check.raw.get("entities", [])
            if isinstance(raw_entities, list):
                entities = raw_entities

    # 3. Inspect check (Script safety)
    script_to_check = req.script if req.script else (req.text if req.check_inspect and any(cmd in req.text for cmd in ["powershell", "Set-MpPreference", "Get-Date", "rm -", "curl", "bash", "sh -c"]) else None)
    if req.check_inspect and script_to_check and overall_decision != "BLOCK":
        inspect_check = await adapter.inspect_script(script_to_check)
        dec, rsn = script_decision(inspect_check)
        inspect_check.outcome = dec
        if dec == "BLOCK":
            overall_decision = "BLOCK"
            reasons.append(rsn)
        elif dec == "HOLD" and overall_decision != "BLOCK":
            overall_decision = "HOLD"
            reasons.append(rsn)

    checks = [c for c in [guard_check, protect_check, inspect_check] if c is not None]
    total_lat = round((time.perf_counter() - started) * 1000, 2)
    total_cred = sum(c.credits for c in checks if c.credits is not None)
    total_cost = sum(c.cost_usd for c in checks if c.cost_usd is not None)
    
    primary_reason = reasons[0] if reasons else "checks_passed"
    if overall_decision == "ALLOW":
        primary_reason = "authorized_action"
    elif overall_decision == "REDACT":
        primary_reason = "personal_data_redacted"

    return ScreenResult(
        decision=overall_decision,
        reason=primary_reason,
        guard=guard_check,
        protect=protect_check,
        inspect=inspect_check,
        redaction_diff=diff_tokens,
        entities_detected=entities,
        total_latency_ms=total_lat,
        total_credits=total_cred,
        total_cost_usd=round(total_cost, 6),
    )
