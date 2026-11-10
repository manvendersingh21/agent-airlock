"""HTTP contract, authenticated reviews, streaming replay and credit bounds."""
import json
import time

import pytest
from fastapi.testclient import TestClient

from airlock.storage import Storage
from main import create_app
from test_gateway import StubAdapter


@pytest.fixture
def client():
    storage = Storage(":memory:")
    with TestClient(create_app(storage=storage, adapter=StubAdapter(), review_token="test-review-token")) as test_client:
        yield test_client
    storage.close()


def finish(client, run_id):
    for _ in range(100):
        run = client.get("/api/runs/" + run_id).json()
        if run["status"] != "RUNNING":
            return run
        time.sleep(.01)
    pytest.fail("run did not complete")


def test_contract_rejects_client_verdicts_and_direct_tool_execution(client):
    scenarios = client.get("/api/scenarios").json()
    assert len(scenarios) == 5 and scenarios[0]["id"] == "poisoned_document"
    for extra in [{"verdict": "benign"}, {"action": {"tool": "send_message"}}, {"approved": True}]:
        assert client.post("/api/runs", json={"scenario_id": "legitimate_request", **extra}).status_code == 422
    assert client.post("/api/tools/execute", json={"tool": "propose_script"}).status_code == 404
    assert client.post("/api/runs", json={"scenario_id": "legitimate_request", "mode": "mock"}).status_code == 422
    assert client.post("/api/runs", json={"scenario_id": "../secret"}).status_code == 404


def test_run_trace_is_persisted_and_sse_resumes_after_last_event(client):
    response = client.post("/api/runs", json={"scenario_id": "legitimate_request", "mode": "protected"})
    assert response.status_code == 202
    completed = finish(client, response.json()["run_id"])
    assert completed["status"] == "ALLOW" and completed["action_executed"]
    events = client.get("/api/runs/" + completed["run_id"] + "/events", headers={"Last-Event-ID": "2"})
    assert events.status_code == 200 and "text/event-stream" in events.headers["content-type"]
    assert "event: complete\n" in events.text and "event: trace\n" in events.text
    assert "id: 1\n" not in events.text and "id: 2\n" not in events.text and "id: 3\n" in events.text
    assert client.get("/api/runs/" + completed["run_id"] + "/events", headers={"Last-Event-ID": "NaN"}).status_code == 400
    assert client.get("/api/runs/unknown/events").status_code == 404
    assert client.get("/api/metrics").json()["checks"] == 3
    assert client.get("/api/runs").json()[0]["run_id"] == completed["run_id"]


def test_reviews_require_separate_reviewer_token_and_digest(client):
    response = client.post("/api/runs", json={"scenario_id": "security_unavailable"})
    held = finish(client, response.json()["run_id"])
    assert held["status"] == "HOLD"
    assert client.get("/api/reviews").status_code == 401
    assert client.get("/api/reviews", headers={"Authorization": "Bearer wrong"}).status_code == 401
    auth = {"Authorization": "Bearer test-review-token"}
    assert len(client.get("/api/reviews", headers=auth).json()) == 1
    route = "/api/reviews/" + held["run_id"] + "/resolve"
    assert client.post(route, json={"decision": "approve", "action_digest": held["action_digest"]}).status_code == 401
    assert client.post(route, json={"decision": "approve", "action_digest": "changed"}, headers=auth).status_code == 409
    reviewed = client.post(route, json={"decision": "approve", "action_digest": held["action_digest"]}, headers=auth)
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "HOLD"
    assert not reviewed.json()["action_executed"]
    assert client.post(route, json={"decision": "approve", "action_digest": held["action_digest"]}, headers=auth).status_code == 409


def test_review_api_disabled_without_configured_token():
    with TestClient(create_app(storage=Storage(":memory:"), adapter=StubAdapter(), review_token="")) as client:
        assert client.get("/api/reviews").status_code == 503


def test_live_run_budget_returns_429_but_failure_drill_does_not_spend_it(monkeypatch):
    monkeypatch.setenv("AIRLOCK_MAX_RUNS_PER_IP_HOUR", "1")
    with TestClient(create_app(storage=Storage(":memory:"), adapter=StubAdapter())) as client:
        first = client.post("/api/runs", json={"scenario_id": "legitimate_request"})
        assert first.status_code == 202
        finish(client, first.json()["run_id"])
        denied = client.post("/api/runs", json={"scenario_id": "legitimate_request"})
        assert denied.status_code == 429 and denied.json()["detail"] == "live_run_budget_exhausted"
        assert client.post("/api/runs", json={"scenario_id": "security_unavailable"}).status_code == 202


def test_empty_metrics_remain_empty(client):
    metrics = client.get("/api/metrics").json()
    assert metrics["checks"] == 0 and metrics["blocked"] == 0
    assert metrics["avg_latency_ms"] is None and metrics["credits"] is None


def test_fake_runtime_mode_is_not_supported(monkeypatch):
    monkeypatch.setenv("AIRLOCK_MODE", "mock")
    with pytest.raises(RuntimeError, match="Only AIRLOCK_MODE=live"):
        with TestClient(create_app(storage=Storage(":memory:"), adapter=StubAdapter())):
            pass
