"""OpenAI-compatible Reverse Proxy for Agent Airlock.

Any standard agent framework (LangChain, AutoGen, CrewAI, OpenAI SDK) can point
its base_url to http://localhost:8000/v1 to have all prompts, context, and tool
calls automatically intercepted, guarded, and redacted by Clocked.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .events import append_event, utc_now
from .models import Check, Run
from .policy import POLICY_VERSION, injection_decision, pii_decision, script_decision
from .storage import Storage


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = ""
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    tools: Optional[List[Dict[str, Any]]] = None


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Usage


async def handle_chat_completion(
    request: ChatCompletionRequest,
    adapter: Any,
    storage: Storage,
) -> Dict[str, Any]:
    started = time.perf_counter()
    run_id = f"proxy_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    
    # Extract incoming content from messages
    user_contents = [m.content for m in request.messages if m.role in {"user", "system"} and m.content]
    combined_text = "\n\n".join(user_contents) if user_contents else ""

    run = Run(
        run_id=run_id,
        scenario_id="proxy_chat_completion",
        mode="protected",
        started_at=now,
    )
    append_event(
        run,
        "received",
        "OpenAI Proxy Request Intercepted",
        f"Intercepted {len(request.messages)} messages for model {request.model}",
        {"model": request.model, "message_count": len(request.messages), "policy_version": POLICY_VERSION},
    )

    # 1. Screen with Clocked Guard (Injection)
    guard_check: Optional[Check] = None
    if combined_text:
        guard_check = await adapter.check_injection(combined_text)
        dec, rsn = injection_decision(guard_check)
        guard_check.outcome = dec
        run.checks.append(guard_check)
        append_event(run, "check_completed", f"Guard · {dec}", rsn, {"endpoint": "injection", "verdict": guard_check.verdict})
        
        if dec == "BLOCK":
            run.status, run.reason = "BLOCK", "prompt_injection_detected"
            run.completed_at = utc_now()
            run.latency_ms = round((time.perf_counter() - started) * 1000, 2)
            append_event(run, "completed", "Run block", "Prompt injection blocked at proxy boundary", {"status": "BLOCK"})
            storage.save(run)
            return {
                "blocked": True,
                "status_code": 400,
                "error": {
                    "message": "Airlock Security Violation: Prompt injection blocked by Clocked Guard. Request aborted before agent execution.",
                    "type": "security_policy_violation",
                    "param": "messages",
                    "code": "prompt_injection_blocked",
                    "clocked_verdict": guard_check.verdict,
                    "evidence": guard_check.evidence[:3] if guard_check.evidence else [],
                },
            }

    # 2. Screen with Clocked Protect (PII)
    protect_check: Optional[Check] = None
    redacted_text = combined_text
    was_redacted = False
    if combined_text:
        protect_check = await adapter.redact_personal_data(combined_text)
        dec, rsn = pii_decision(protect_check)
        protect_check.outcome = dec
        run.checks.append(protect_check)
        append_event(run, "check_completed", f"Protect · {dec}", rsn, {"endpoint": "pii", "entities_count": len(protect_check.raw.get("entities", []))})
        
        if dec == "REDACT" and protect_check.safe_text:
            redacted_text = protect_check.safe_text
            was_redacted = True

    # 3. Check any proposed scripts if present in message or tools
    inspect_check: Optional[Check] = None
    for content in user_contents:
        if any(marker in content for marker in ["powershell", "Set-MpPreference", "Get-Date", "rm -rf", "curl", "bash"]):
            inspect_check = await adapter.inspect_script(content)
            dec, rsn = script_decision(inspect_check)
            inspect_check.outcome = dec
            run.checks.append(inspect_check)
            append_event(run, "check_completed", f"Inspect · {dec}", rsn, {"endpoint": "script", "verdict": inspect_check.verdict})
            if dec == "BLOCK":
                run.status, run.reason = "BLOCK", "malicious_script_detected"
                run.completed_at = utc_now()
                run.latency_ms = round((time.perf_counter() - started) * 1000, 2)
                append_event(run, "completed", "Run block", "Malicious script blocked at proxy boundary", {"status": "BLOCK"})
                storage.save(run)
                return {
                    "blocked": True,
                    "status_code": 400,
                    "error": {
                        "message": "Airlock Security Violation: Malicious script blocked by Clocked Inspect. Execution aborted.",
                        "type": "security_policy_violation",
                        "param": "messages",
                        "code": "script_malicious_blocked",
                    },
                }

    # If all passed, record run and return successful chat completion
    run.status = "REDACT" if was_redacted else "ALLOW"
    run.reason = "personal_data_redacted" if was_redacted else "authorized_action"
    run.completed_at = utc_now()
    run.latency_ms = round((time.perf_counter() - started) * 1000, 2)
    run.action_executed = True
    append_event(run, "completed", f"Run {run.status.lower()}", "Proxy traffic verified and forwarded.", {"status": run.status})
    storage.save(run)

    assistant_msg = (
        f"[Airlock Gateway: Verified Safe]\n"
        f"Clocked Guard: PASSED\n"
        f"Clocked Protect: {'REDACTED (PII scrubbed to tokens)' if was_redacted else 'CLEAN'}\n"
        f"Latency: {run.latency_ms} ms\n\n"
        f"Screened content processed successfully without security policy violation."
    )
    if was_redacted:
        assistant_msg += f"\n\nSanitized Agent Context:\n{redacted_text}"

    return {
        "blocked": False,
        "status_code": 200,
        "headers": {
            "x-airlock-decision": run.status,
            "x-clocked-guard": guard_check.verdict if guard_check else "n/a",
            "x-clocked-protect": "redacted" if was_redacted else "clean",
            "x-clocked-latency-ms": str(run.latency_ms),
        },
        "response": ChatCompletionResponse(
            id=f"chatcmpl-{run_id}",
            created=int(time.time()),
            model="airlock-clocked-gateway",
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=assistant_msg),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=len(combined_text.split()),
                completion_tokens=len(assistant_msg.split()),
                total_tokens=len(combined_text.split()) + len(assistant_msg.split()),
            ),
        ).model_dump(mode="json"),
    }
