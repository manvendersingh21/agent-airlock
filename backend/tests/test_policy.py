"""Policy tests use explicitly synthetic verdicts; no detector accuracy claims."""
import pytest

from airlock.models import Action, Check
from airlock.policy import action_digest, authorize_action, injection_decision, pii_decision, script_decision
from airlock.simulated_tools import SimulatedTools, ToolDenied


@pytest.mark.parametrize("endpoint,policy,verdict,expected", [
    ("injection", injection_decision, "benign", "ALLOW"),
    ("injection", injection_decision, "injection", "BLOCK"),
    ("script", script_decision, "benign", "ALLOW"),
    ("script", script_decision, "malicious", "BLOCK"),
    ("script", script_decision, "suspicious", "HOLD"),
])
def test_recognized_labels(endpoint, policy, verdict, expected):
    check = Check(endpoint=endpoint, input_text="test", verdict=verdict, raw={"verdict": verdict})
    assert policy(check)[0] == expected


@pytest.mark.parametrize("verdict", [None, "", "safe", "allow", "BENIGN", "benign ", "unknown"])
@pytest.mark.parametrize("endpoint,policy", [("injection", injection_decision), ("script", script_decision)])
def test_no_aliases_for_explicit_benign(endpoint, policy, verdict):
    assert policy(Check(endpoint=endpoint, input_text="test", verdict=verdict, raw={"verdict": verdict}))[0] == "HOLD"


def test_normalized_verdict_cannot_override_raw_verdict():
    check = Check(endpoint="injection", input_text="x", verdict="benign", raw={"verdict": "injection"})
    assert injection_decision(check) == ("HOLD", "invalid_security_response")


@pytest.mark.parametrize("safe", [None, 12, [], {}])
def test_pii_requires_string_output(safe):
    check = Check(endpoint="pii", input_text="raw private", raw={"anonymized_text": safe})
    assert pii_decision(check)[0] == "HOLD"


def test_pii_changed_and_clean_copy():
    redacted = Check(endpoint="pii", input_text="Jane", safe_text="<PERSON>", raw={"anonymized_text": "<PERSON>"})
    assert pii_decision(redacted)[0] == "REDACT"
    clean = Check(endpoint="pii", input_text="printer", safe_text="printer", raw={"anonymized_text": "printer"})
    assert pii_decision(clean)[0] == "ALLOW"


def test_digest_is_stable_for_argument_order_and_changes_on_mutation():
    action = Action(tool="send_message", arguments={"recipient": "a", "body": "b"})
    reordered = Action(tool="send_message", arguments={"body": "b", "recipient": "a"})
    assert action_digest(action) == action_digest(reordered)
    reordered.arguments["body"] = "new payload"
    assert action_digest(action) != action_digest(reordered)


@pytest.mark.parametrize("action,capabilities,reason", [
    (Action(tool="record_action", arguments={"kind": "support_summary"}), [], "tool_not_authorized"),
    (Action(tool="send_message", arguments={"recipient": "example.invalid", "body": "x"}), ["send_message"], "outbound_messages_not_authorized"),
    (Action(tool="propose_script", arguments={"script": "Get-Date; malicious"}), ["propose_script"], "script_not_allowlisted"),
    (Action(tool="propose_script", arguments={"script": "Get-Date", "extra": "x"}), ["propose_script"], "invalid_tool_arguments"),
    (Action(tool="record_action", arguments={"kind": "support_summary", "original_input": "private"}), ["record_action"], "invalid_tool_arguments"),
    (Action(tool="read_document", arguments={"document_id": "../../secret"}), ["read_document"], "document_not_authorized"),
])
def test_capabilities_and_exact_argument_allowlists(action, capabilities, reason):
    assert authorize_action(action, capabilities) == ("BLOCK", reason)


def test_modified_approved_action_cannot_invoke_tool():
    tools = SimulatedTools()
    action = Action(tool="propose_script", arguments={"script": "Get-Date"})
    digest = action_digest(action)
    action.arguments["script"] = "Get-Process | Select-Object Name, Id"
    with pytest.raises(ToolDenied, match="action_changed_after_approval"):
        tools.execute(action, approved_digest=digest, capabilities=["propose_script"], agent_input="screened")
    assert tools.invocations == 0


def test_even_matching_digest_cannot_grant_unsupported_capability():
    action = Action(tool="propose_script", arguments={"script": "Get-Date"})
    tools = SimulatedTools()
    with pytest.raises(ToolDenied, match="tool_not_authorized"):
        tools.execute(action, approved_digest=action_digest(action), capabilities=[], agent_input="screened")
    assert tools.invocations == 0
