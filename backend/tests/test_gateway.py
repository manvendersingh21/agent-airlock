"""Enforcement integration tests with a labeled deterministic test adapter."""
import asyncio

import pytest

from airlock.gateway import Gateway, ReviewConflict, load_scenarios
from airlock.models import Check, ReviewResolution
from airlock.storage import Storage


class StubAdapter:
    """Testing only; never imported by runtime."""
    def __init__(self, injection="benign", script="benign", safe_text=None, fail_at=None, error="security_check_unavailable"):
        self.injection = injection
        self.script = script
        self.safe_text = safe_text
        self.fail_at = fail_at
        self.error = error
        self.calls = []

    def result(self, endpoint, text, **kwargs):
        self.calls.append((endpoint, text))
        if endpoint == self.fail_at:
            return Check(endpoint=endpoint, input_text=text, status="error", error=self.error)
        return Check(endpoint=endpoint, input_text=text, latency_ms=5, model_ms=2, credits=1, cost_usd=.001, **kwargs)

    async def check_injection(self, text):
        return self.result("injection", text, verdict=self.injection, raw={"verdict": self.injection})

    async def redact_personal_data(self, text):
        safe = self.safe_text if self.safe_text is not None else text
        return self.result("pii", text, safe_text=safe, raw={"anonymized_text": safe})

    async def inspect_script(self, text):
        return self.result("script", text, verdict=self.script, raw={"verdict": self.script})


def make_gateway(adapter=None):
    return Gateway(Storage(":memory:"), adapter or StubAdapter())


async def run_scenario(gateway, name, mode="protected"):
    run = gateway.create_run(name, mode)
    return await gateway.process(run.run_id)


@pytest.mark.asyncio
async def test_injection_stops_before_agent_and_tool_and_is_persisted():
    adapter = StubAdapter(injection="injection")
    gateway = make_gateway(adapter)
    run = await run_scenario(gateway, "poisoned_document")
    assert run.status == "BLOCK" and run.reason == "prompt_injection_detected"
    assert run.agent_input is None and run.proposed_action is None
    assert not run.action_executed and gateway.tools.invocations == 0
    assert [endpoint for endpoint, _ in adapter.calls] == ["injection"]
    stored = gateway.storage.get(run.run_id)
    assert stored == run
    assert [event.id for event in run.events] == list(range(1, len(run.events) + 1))
    assert run.events[-1].type == "completed"


@pytest.mark.asyncio
async def test_redacted_copy_is_the_only_agent_and_tool_context():
    safe = "Customer <PERSON>; email <EMAIL>. The office printer is offline."
    gateway = make_gateway(StubAdapter(safe_text=safe))
    seen = []
    original = gateway.agent.propose
    def spy(agent_input, plan):
        seen.append(agent_input)
        return original(agent_input, plan)
    gateway.agent.propose = spy
    run = await run_scenario(gateway, "privacy_leak")
    assert run.status == "REDACT" and run.action_executed
    assert seen == [safe] and run.agent_input == safe
    assert run.tool_result["recorded_context"] == safe
    assert "Maya Chen" not in str(run.tool_result)
    assert gateway.tools.invocations == 1


@pytest.mark.asyncio
async def test_script_inspected_before_simulation():
    adapter = StubAdapter(script="malicious")
    gateway = make_gateway(adapter)
    run = await run_scenario(gateway, "dangerous_script")
    assert run.status == "BLOCK" and run.reason == "malicious_script_detected"
    assert [endpoint for endpoint, _ in adapter.calls] == ["injection", "pii", "script"]
    assert gateway.tools.invocations == 0 and not run.action_executed


@pytest.mark.asyncio
async def test_false_negative_detector_cannot_authorize_dangerous_script():
    gateway = make_gateway()
    run = await run_scenario(gateway, "dangerous_script")
    assert run.status == "BLOCK" and run.reason == "script_not_allowlisted"
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
async def test_false_negative_detector_cannot_authorize_exfiltration():
    gateway = make_gateway()
    run = await run_scenario(gateway, "poisoned_document")
    assert run.status == "BLOCK" and run.reason == "tool_not_authorized"
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
async def test_benign_run_allows_exactly_once_with_realistic_metrics():
    gateway = make_gateway()
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "ALLOW" and run.action_executed
    assert gateway.tools.invocations == 1
    assert await gateway.process(run.run_id) == run
    assert gateway.tools.invocations == 1
    metrics = gateway.storage.metrics()
    assert metrics.checks == 3 and metrics.allowed == 1 and metrics.protected_runs == 1
    assert metrics.credits == 3 and metrics.cost_usd == .003 and metrics.avg_latency_ms == 5


@pytest.mark.asyncio
async def test_failure_drill_calls_no_live_adapter():
    adapter = StubAdapter()
    gateway = make_gateway(adapter)
    run = await run_scenario(gateway, "security_unavailable")
    assert run.status == "HOLD" and run.reason == "security_check_unavailable"
    assert adapter.calls == [] and gateway.tools.invocations == 0
    assert any(event.data.get("injected_failure") for event in run.events)


@pytest.mark.asyncio
async def test_baseline_is_honest_simulation_without_clocked_or_protected_tools():
    adapter = StubAdapter()
    gateway = make_gateway(adapter)
    run = await run_scenario(gateway, "poisoned_document", "baseline")
    assert run.status == "BASELINE" and "Deterministic simulation" in run.baseline_label
    assert run.tool_result["simulated"] is True
    assert run.checks == [] and adapter.calls == [] and gateway.tools.invocations == 0
    metrics = gateway.storage.metrics()
    assert metrics.runs == 1 and metrics.protected_runs == 0 and metrics.checks == 0
    assert metrics.credits is None and metrics.avg_latency_ms is None


@pytest.mark.asyncio
async def test_changed_proposal_after_run_creation_blocks():
    gateway = make_gateway()
    run = gateway.create_run("legitimate_request")
    gateway.scenarios["legitimate_request"].proposed_action.arguments["script"] = "Get-Process | Select-Object Name, Id"
    completed = await gateway.process(run.run_id)
    assert completed.status == "BLOCK" and completed.reason == "action_changed_after_approval"
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
async def test_agent_cannot_change_approved_action_before_execution():
    gateway = make_gateway()
    def changed_action(context, plan):
        changed = plan.model_copy(deep=True)
        changed.arguments["script"] = "Get-Process | Select-Object Name, Id"
        return changed
    gateway.agent.propose = changed_action
    run = await run_scenario(gateway, "legitimate_request")
    assert run.status == "BLOCK" and run.reason == "action_changed_after_approval"
    assert gateway.tools.invocations == 0


@pytest.mark.asyncio
async def test_human_approval_revalidates_and_cannot_bypass_failure():
    gateway = make_gateway(StubAdapter(fail_at="script"))
    held = await run_scenario(gateway, "legitimate_request")
    before = len(held.checks)
    reviewed = await gateway.resolve_review(held.run_id, ReviewResolution(decision="approve", action_digest=held.action_digest))
    assert reviewed.status == "HOLD" and not reviewed.action_executed
    assert len(reviewed.checks) == before + 3 and gateway.tools.invocations == 0
    with pytest.raises(ReviewConflict):
        await gateway.resolve_review(held.run_id, ReviewResolution(decision="approve", action_digest=held.action_digest))


@pytest.mark.asyncio
async def test_human_approval_after_service_recovery_runs_checks_then_executes_once():
    adapter = StubAdapter(fail_at="injection")
    gateway = make_gateway(adapter)
    held = await run_scenario(gateway, "legitimate_request")
    adapter.fail_at = None
    reviewed = await gateway.resolve_review(held.run_id, ReviewResolution(decision="approve", action_digest=held.action_digest))
    assert reviewed.status == "ALLOW" and gateway.tools.invocations == 1
    assert len(reviewed.checks) == 4
    assert gateway.storage.pending_reviews() == []
    with pytest.raises(ReviewConflict):
        await gateway.resolve_review(held.run_id, ReviewResolution(decision="approve", action_digest=held.action_digest))
    assert gateway.tools.invocations == 1


@pytest.mark.asyncio
async def test_review_digest_mismatch_does_not_consume_review_or_call_adapter():
    adapter = StubAdapter(fail_at="injection")
    gateway = make_gateway(adapter)
    held = await run_scenario(gateway, "legitimate_request")
    with pytest.raises(ReviewConflict, match="action_digest_mismatch"):
        await gateway.resolve_review(held.run_id, ReviewResolution(decision="approve", action_digest="modified"))
    assert len(adapter.calls) == 1 and len(gateway.storage.pending_reviews()) == 1


@pytest.mark.asyncio
async def test_reviewer_denial_stops_permanently():
    gateway = make_gateway(StubAdapter(fail_at="injection"))
    held = await run_scenario(gateway, "legitimate_request")
    denied = await gateway.resolve_review(held.run_id, ReviewResolution(decision="deny", action_digest=held.action_digest, note="Reject this action."))
    assert denied.status == "BLOCK" and denied.reason == "reviewer_denied"
    assert gateway.tools.invocations == 0 and gateway.storage.pending_reviews() == []


def test_persistence_and_restart_fail_closed(tmp_path):
    path = str(tmp_path / "audit.db")
    gateway = Gateway(Storage(path), StubAdapter())
    pending = gateway.create_run("legitimate_request")
    gateway.storage.close()
    reopened = Storage(path)
    assert reopened.recover_interrupted() == 1
    assert reopened.get(pending.run_id).status == "HOLD"
    assert reopened.get(pending.run_id).reason == "gateway_restarted"
    assert not reopened.get(pending.run_id).action_executed
    reopened.close()


@pytest.mark.asyncio
async def test_real_tools_outbox_and_tickets_execution():
    storage = Storage("sqlite:///:memory:")
    adapter = StubAdapter()
    gateway = Gateway(storage, adapter)

    # Baseline poisoned document actually delivers message to outbox
    baseline_run = await run_scenario(gateway, "poisoned_document", mode="baseline")
    assert baseline_run.action_executed
    outbox = storage.list_outbox()
    assert len(outbox) == 1
    assert outbox[0]["recipient"] == "audit-drop@example.invalid"

    # Protected poisoned document is BLOCKED: zero new messages in outbox
    protected_run = await run_scenario(gateway, "poisoned_document", mode="protected")
    assert protected_run.status == "BLOCK"
    assert not protected_run.action_executed
    assert len(storage.list_outbox()) == 1

    # Protected privacy leak stores sanitized ticket
    gateway_pii = Gateway(storage, StubAdapter(safe_text="Customer: [NAME_1]; email: [EMAIL_1]. The office printer is offline."))
    privacy_run = await run_scenario(gateway_pii, "privacy_leak", mode="protected")
    assert privacy_run.status == "REDACT"
    assert privacy_run.action_executed
    tickets = storage.list_tickets()
    assert len(tickets) == 1
    assert tickets[0]["pii_scrubbed"] is True
    assert "Maya Chen" not in tickets[0]["customer_name"]

    # Protected legitimate request executes real script runner in sandbox
    benign_run = await run_scenario(gateway, "legitimate_request", mode="protected")
    assert benign_run.status == "ALLOW"
    assert benign_run.action_executed
    assert benign_run.tool_result["executed"] is True
    assert benign_run.tool_result["exit_code"] == 0
    assert len(benign_run.tool_result["stdout"]) > 0

