"""Deterministic policy. Detector output never grants tool capabilities."""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Tuple

from .models import Action, Check, Decision

SAFE_SCRIPTS = frozenset({"Get-Date", "Get-Process | Select-Object Name, Id"})
RECORD_KINDS = frozenset({"support_summary", "maintenance_summary", "summary", "audit_note"})
POLICY_VERSION = "airlock-policy-1"


def _unavailable(check: Check):
    if check.status != "ok" or check.error:
        reason = "invalid_security_response" if check.error == "invalid_security_response" else "security_check_unavailable"
        return "HOLD", reason
    return None


def injection_decision(check: Check) -> Tuple[Decision, str]:
    failure = _unavailable(check)
    if failure:
        return failure
    if check.endpoint != "injection" or check.raw.get("verdict") != check.verdict:
        return "HOLD", "invalid_security_response"
    if check.verdict == "benign":
        return "ALLOW", "injection_check_passed"
    if check.verdict == "injection":
        return "BLOCK", "prompt_injection_detected"
    return "HOLD", "unrecognized_injection_verdict"


def pii_decision(check: Check) -> Tuple[Decision, str]:
    failure = _unavailable(check)
    if failure:
        return failure
    safe = check.raw.get("anonymized_text")
    if check.endpoint != "pii" or not isinstance(safe, str) or safe != check.safe_text:
        return "HOLD", "invalid_security_response"
    if safe != check.input_text:
        return "REDACT", "personal_data_redacted"
    return "ALLOW", "privacy_check_passed"


def script_decision(check: Check) -> Tuple[Decision, str]:
    failure = _unavailable(check)
    if failure:
        return failure
    if check.endpoint != "script" or check.raw.get("verdict") != check.verdict:
        return "HOLD", "invalid_security_response"
    if check.verdict == "benign":
        return "ALLOW", "script_check_passed"
    if check.verdict == "malicious":
        return "BLOCK", "malicious_script_detected"
    if check.verdict == "suspicious":
        return "HOLD", "suspicious_script_requires_review"
    return "HOLD", "unrecognized_script_verdict"


def action_digest(action: Action) -> str:
    encoded = json.dumps(action.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def authorize_action(action: Action, capabilities: Iterable[str]) -> Tuple[Decision, str]:
    if action.tool not in capabilities:
        return "BLOCK", "tool_not_authorized"
    args = action.arguments
    if action.tool == "send_message":
        return "BLOCK", "outbound_messages_not_authorized"
    if action.tool == "propose_script":
        if set(args) != {"script"} or not isinstance(args.get("script"), str):
            return "BLOCK", "invalid_tool_arguments"
        if args["script"] not in SAFE_SCRIPTS:
            return "BLOCK", "script_not_allowlisted"
    elif action.tool == "record_action":
        if set(args) != {"kind"} or not isinstance(args.get("kind"), str) or args["kind"] not in RECORD_KINDS:
            return "BLOCK", "invalid_tool_arguments"
    elif action.tool == "read_document":
        if set(args) != {"document_id"} or args.get("document_id") != "screened_document":
            return "BLOCK", "document_not_authorized"
    else:
        return "BLOCK", "unsupported_tool"
    return "ALLOW", "authorized_simulated_action"
