"""Failure cases test tool non-invocation, not just red badges."""
import asyncio

import pytest
from clocked_sdk import APIConnectionError, AuthenticationError, InsufficientCreditsError, PermissionDeniedError, RateLimitError, RequestTimeoutError, Result, ServerError

from airlock.clocked_adapter import ClockedAdapter
from airlock.gateway import Gateway
from airlock.storage import Storage
from test_gateway import StubAdapter, make_gateway, run_scenario


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["injection", "pii", "script"])
@pytest.mark.parametrize("error", ["security_check_unavailable", "invalid_security_response"])
async def test_failure_at_every_boundary_prevents_tool_invocation(stage, error):
    gateway = make_gateway(StubAdapter(fail_at=stage, error=error))
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "HOLD" and run.reason == error
    assert not run.action_executed and gateway.tools.invocations == 0
    if stage in {"injection", "pii"}:
        assert run.agent_input is None


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["injection", "script"])
async def test_unknown_verdict_at_every_classifier_holds(stage):
    adapter = StubAdapter(**{stage: "unexpected-new-label"})
    gateway = make_gateway(adapter)
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "HOLD" and not run.action_executed
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("error_class,code", [
    (AuthenticationError, 401), (InsufficientCreditsError, 402),
    (PermissionDeniedError, 403), (RateLimitError, 429),
    (ServerError, 500), (APIConnectionError, None), (RequestTimeoutError, None),
])
async def test_real_sdk_error_types_never_reach_tool(error_class, code):
    class FailingClient:
        async def injection(self, **kwargs):
            raise error_class("sensitive upstream detail", status=code)
    gateway = Gateway(Storage(":memory:"), ClockedAdapter(FailingClient()))
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "HOLD" and run.reason == "security_check_unavailable"
    assert not run.action_executed and gateway.tools.invocations == 0
    assert "sensitive upstream detail" not in run.model_dump_json()


@pytest.mark.asyncio
async def test_unexpected_adapter_exception_is_sanitized_and_held():
    class BrokenAdapter(StubAdapter):
        async def check_injection(self, text):
            raise RuntimeError("credential-must-stay-private")
    gateway = make_gateway(BrokenAdapter())
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "HOLD" and not run.action_executed
    assert "credential-must-stay-private" not in run.model_dump_json()


@pytest.mark.asyncio
async def test_cancelled_security_call_records_hold():
    entered = asyncio.Event()
    class SlowAdapter(StubAdapter):
        async def check_injection(self, text):
            entered.set()
            await asyncio.Event().wait()
    gateway = make_gateway(SlowAdapter())
    run = gateway.create_run("legitimate_request")
    task = asyncio.create_task(gateway.process(run.run_id))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    stored = gateway.storage.get(run.run_id)
    assert stored.status == "HOLD" and stored.reason == "gateway_interrupted"
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
async def test_wrong_check_identity_is_not_reusable_approval():
    class WrongAdapter(StubAdapter):
        async def check_injection(self, text):
            return await super().check_injection("a different input")
    gateway = make_gateway(WrongAdapter())
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "HOLD" and run.reason == "invalid_security_response"
    assert gateway.tools.invocations == 0
