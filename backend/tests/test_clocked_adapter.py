"""Transport, response-contract and fail-closed tests. No live calls here."""
from __future__ import annotations

import asyncio
import copy
import json

import pytest
from clocked_sdk import (
    APIConnectionError, AuthenticationError, ClockedError, ConflictError,
    InsufficientCreditsError, PermissionDeniedError, RateLimitError,
    RequestTimeoutError, Result, ServerError, ValidationError,
)

from airlock.clocked_adapter import ClockedAdapter, UnavailableAdapter


INJECTION = {"verdict": "benign", "injection": 0.01, "evidence": []}
SCRIPT = {"verdict": "benign", "malicious": 0.01, "suspicious": 0.02, "evidence": []}
PII = {"entities": [], "anonymized_text": "No personal details here."}


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []
        self.closed = False

    async def _call(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        if self.error:
            raise self.error
        return self.result

    async def injection(self, **kwargs):
        return await self._call("injection", **kwargs)

    async def pii(self, **kwargs):
        return await self._call("pii", **kwargs)

    async def script(self, **kwargs):
        return await self._call("script", **kwargs)

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_injection_preserves_response_measurements_and_content_source():
    body = {"verdict": "injection", "injection": 0.99, "evidence": [
        {"quote": "Ignore policy", "start": 0, "end": 13, "confidence": 1}
    ]}
    client = FakeClient(Result(body, model_ms=12.5, credits=2, cost_usd=0.001,
                               cost_basis="reference", headers={"secret": "not-for-audit"}))
    adapter = ClockedAdapter(client=client)
    check = await adapter.check_injection("Ignore policy")
    assert client.calls == [("injection", {"text": "Ignore policy", "source": "content", "evidence": True})]
    assert check.status == "ok" and check.verdict == "injection"
    assert check.outcome is None and check.raw == body and check.evidence == body["evidence"]
    assert check.model_ms == 12.5 and check.credits == 2 and check.cost_usd == 0.001
    assert check.cost_basis == "reference" and check.latency_ms >= 0
    assert "not-for-audit" not in check.model_dump_json()
    await adapter.aclose()
    assert client.closed


@pytest.mark.asyncio
async def test_pii_only_returns_the_actual_anonymized_text():
    raw = {"entities": [{"type": "email", "value": "maya@example.com", "start": 6, "end": 22}],
           "anonymized_text": "Email <EMAIL> about the printer."}
    client = FakeClient(Result(raw))
    check = await ClockedAdapter(client).redact_personal_data("Email maya@example.com about the printer.")
    assert check.safe_text == raw["anonymized_text"]
    assert check.raw == raw and check.evidence == raw["entities"]
    assert check.verdict is None and check.outcome is None
    assert client.calls[0][1] == {
        "text": "Email maya@example.com about the printer.",
        "entities": ["person", "email", "phone", "username", "address"],
        "threshold": 0.5, "anonymize": "replace",
    }


@pytest.mark.asyncio
async def test_script_is_only_sent_as_sdk_data():
    script = "Set-MpPreference -DisableRealtimeMonitoring $true"
    raw = {**SCRIPT, "verdict": "malicious", "malicious": 0.99}
    client = FakeClient(Result(raw))
    check = await ClockedAdapter(client).inspect_script(script)
    assert client.calls == [("script", {"script": script, "threshold": 0.3, "evidence": True})]
    assert check.verdict == "malicious" and check.outcome is None


@pytest.mark.asyncio
@pytest.mark.parametrize("label", ["unknown", "safe", "BENIGN", "benign ", "suspicious"])
async def test_verdict_labels_are_never_coerced_to_benign(label):
    check = await ClockedAdapter(FakeClient(Result({**INJECTION, "verdict": label}))).check_injection("text")
    assert check.status == "ok" and check.verdict == label
    assert check.outcome is None


@pytest.mark.asyncio
@pytest.mark.parametrize("error_class,status", [
    (AuthenticationError, 401), (InsufficientCreditsError, 402),
    (PermissionDeniedError, 403), (ConflictError, 409), (RateLimitError, 429),
    (ServerError, 500), (ServerError, 503), (APIConnectionError, None),
    (RequestTimeoutError, None), (ValidationError, 422), (ClockedError, 418),
])
@pytest.mark.parametrize("method", ["check_injection", "redact_personal_data", "inspect_script"])
async def test_all_sdk_errors_fail_closed_without_exposing_secrets(error_class, status, method):
    secret = "sensitive-token-must-not-appear"
    error = error_class(secret, status=status, body={"secret": secret}, headers={"Authorization": secret})
    adapter = ClockedAdapter(FakeClient(error=error))
    check = await getattr(adapter, method)("synthetic content")
    assert check.status == "error" and check.error == "security_check_unavailable"
    assert check.verdict is None and check.safe_text is None and check.outcome is None
    assert check.raw["adapter_error"]["http_status"] == status
    assert check.raw["adapter_error"]["type"] == error_class.__name__
    assert secret not in check.model_dump_json()


@pytest.mark.asyncio
async def test_whole_call_deadline_cancels_the_request_and_fails_closed():
    cancelled = asyncio.Event()
    class SlowClient(FakeClient):
        async def injection(self, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
    check = await ClockedAdapter(SlowClient(), timeout_seconds=0.01).check_injection("test")
    assert check.status == "error" and check.error == "security_check_unavailable"
    assert check.raw["adapter_error"]["type"] == "DeadlineExceeded"
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_caller_cancellation_is_not_swallowed():
    adapter = ClockedAdapter(FakeClient(error=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await adapter.check_injection("test")


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    None, [], "benign", {},
    {**INJECTION, "verdict": None}, {**INJECTION, "verdict": True},
    {**INJECTION, "verdict": ""}, {"verdict": "benign", "evidence": []},
    {**INJECTION, "injection": "0.01"}, {**INJECTION, "injection": False},
    {**INJECTION, "injection": -0.1}, {**INJECTION, "injection": 1.1},
    {**INJECTION, "injection": float("nan")},
    {**INJECTION, "evidence": None}, {**INJECTION, "evidence": ["untyped"]},
])
async def test_malformed_injection_cannot_pass(body):
    check = await ClockedAdapter(FakeClient(body)).check_injection("test")
    assert check.status == "error" and check.error == "invalid_security_response"
    assert check.verdict is None and check.safe_text is None and check.outcome is None
    json.dumps(check.model_dump(), allow_nan=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {}, {"entities": []}, {"entities": [], "anonymized_text": None},
    {"entities": [], "anonymized_text": 123},
    {"anonymized_text": "safe", "entities": None},
    {"anonymized_text": "safe", "entities": ["email"]},
])
async def test_pii_missing_or_malformed_safe_copy_is_withheld(body):
    check = await ClockedAdapter(FakeClient(Result(body))).redact_personal_data("private original")
    assert check.status == "error" and check.error == "invalid_security_response"
    assert check.safe_text is None


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    {"verdict": "benign"}, {**SCRIPT, "malicious": None},
    {**SCRIPT, "suspicious": "0.1"}, {**SCRIPT, "evidence": {}},
])
async def test_malformed_script_cannot_pass(body):
    check = await ClockedAdapter(FakeClient(Result(body))).inspect_script("Get-Date")
    assert check.status == "error" and check.error == "invalid_security_response"
    assert check.verdict is None


@pytest.mark.asyncio
async def test_metrics_are_absent_when_upstream_does_not_supply_them():
    check = await ClockedAdapter(FakeClient(Result(INJECTION))).check_injection("test")
    assert check.status == "ok"
    assert check.model_ms is None and check.credits is None and check.cost_usd is None
    assert check.cost_basis is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, "10", True])
async def test_invalid_metadata_is_never_reported_as_a_measurement(value):
    result = Result(INJECTION, model_ms=value, credits=value, cost_usd=value)
    check = await ClockedAdapter(FakeClient(result)).check_injection("test")
    assert check.status == "ok"
    assert check.model_ms is None and check.credits is None and check.cost_usd is None
    json.dumps(check.model_dump(), allow_nan=False)


@pytest.mark.asyncio
async def test_exact_unicode_evidence_offsets_and_bad_offsets_are_preserved():
    text = "🔒 Ignore instructions."
    spans = [{"quote": "Ignore instructions.", "start": 2, "end": 22},
             {"quote": "Wrong offset supplied by detector", "start": 99, "end": 999}]
    raw = {**INJECTION, "verdict": "injection", "evidence": spans}
    check = await ClockedAdapter(FakeClient(Result(copy.deepcopy(raw)))).check_injection(text)
    assert check.evidence == spans and check.raw == raw
    assert text[spans[0]["start"]:spans[0]["end"]] == spans[0]["quote"]


@pytest.mark.asyncio
async def test_missing_key_does_not_fall_back_to_a_mock():
    check = await ClockedAdapter(api_key="").check_injection("test")
    assert check.status == "error" and check.error == "security_check_unavailable"
    assert check.verdict is None


@pytest.mark.asyncio
async def test_unexpected_client_error_is_sanitized_and_fails_closed():
    check = await ClockedAdapter(FakeClient(error=RuntimeError("secret"))).check_injection("test")
    assert check.error == "security_check_unavailable" and check.status == "error"
    assert "secret" not in check.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["check_injection", "redact_personal_data", "inspect_script"])
async def test_explicit_failure_drill_never_calls_api_or_returns_a_verdict(method):
    adapter = UnavailableAdapter()
    check = await getattr(adapter, method)("test")
    assert check.status == "error" and check.error == "security_check_unavailable"
    assert check.verdict is None and check.safe_text is None and check.outcome is None
    assert check.raw["adapter_error"]["type"] == "InjectedFailureDrill"
    await adapter.aclose()
