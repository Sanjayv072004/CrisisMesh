"""Unit and Security Tests for Agent Framework, Permissions, Message Bus, and LLM Adapter."""
import pytest
from pydantic import BaseModel, Field, ValidationError
from backend.app.models.message import Message
from backend.app.security.manifest import PermissionManifest, PermissionViolation
from backend.app.agents.base.bus import MessageBus
from backend.app.agents.base.agent import BaseAgent
from backend.app.agents.base.llm_adapter import LLMAdapter, LLMMode


class DummySituationAgent(BaseAgent):
    """Concrete test agent inheriting BaseAgent."""
    def run(self, state):
        return state


class SampleExtractionSchema(BaseModel):
    incident_type: str
    severity: int = Field(ge=1, le=5)
    location_name: str
    is_life_threatening: bool


def test_disallowed_tool_call_is_blocked_and_appears_in_trace():
    """Test 1: Disallowed tool call raises PermissionViolation and publishes a security event to trace."""
    bus = MessageBus()
    manifest = PermissionManifest(
        allowed_tools={"legitimate_data_cleaner"},
        allowed_inbound={"ReportReceived"},
        allowed_outbound={"IncidentParsed"}
    )
    tools = {
        "legitimate_data_cleaner": lambda text: text.strip(),
        "unauthorized_root_executor": lambda cmd: f"Executed {cmd}"
    }

    agent = DummySituationAgent(
        name="Situation",
        role="Report Extractor",
        manifest=manifest,
        bus=bus,
        tools=tools
    )

    trace_id = "trace-sec-audit-001"

    # 1. Allowed tool must succeed
    cleaned = agent.call_tool("legitimate_data_cleaner", trace_id=trace_id, text="  water flood  ")
    assert cleaned == "water flood"

    # 2. Unauthorized tool must raise PermissionViolation
    with pytest.raises(PermissionViolation) as exc_info:
        agent.call_tool("unauthorized_root_executor", trace_id=trace_id, cmd="rm -rf /")

    assert "unauthorized" in str(exc_info.value).lower()
    assert exc_info.value.agent_name == "Situation"
    assert exc_info.value.item_name == "unauthorized_root_executor"

    # 3. Security violation event must appear in the message bus trace
    trace = bus.get_trace(trace_id=trace_id)
    security_events = [m for m in trace if m.type == "SecurityViolation"]
    assert len(security_events) == 1, "Expected exactly 1 security event in trace"
    sec_event = security_events[0]
    assert sec_event.sender == "Situation"
    assert sec_event.receiver == "Guardian"
    assert sec_event.payload["target_tool"] == "unauthorized_root_executor"
    assert "legitimate_data_cleaner" in sec_event.payload["allowed_tools"]


def test_mock_mode_is_deterministic():
    """Test 2: LLMAdapter in MOCK mode is 100% deterministic and schema-valid offline."""
    adapter = LLMAdapter(mode=LLMMode.MOCK)
    prompt = "Elderly citizen trapped on roof near Bellandur lake with water level rising to 4 feet."

    # Call 1
    res1 = adapter.generate(
        agent_name="Situation",
        prompt=prompt,
        schema=SampleExtractionSchema,
        trace_id="mock-trace-1"
    )

    # Call 2 (Same prompt and agent)
    res2 = adapter.generate(
        agent_name="Situation",
        prompt=prompt,
        schema=SampleExtractionSchema,
        trace_id="mock-trace-2"
    )

    # Must be schema valid
    assert isinstance(res1, SampleExtractionSchema)
    assert isinstance(res2, SampleExtractionSchema)

    # Must be 100% identical and deterministic
    assert res1.model_dump() == res2.model_dump()

    # Test registered canned response
    canned = SampleExtractionSchema(
        incident_type="flood",
        severity=4,
        location_name="Bellandur EcoSpace",
        is_life_threatening=True
    )
    adapter.register_canned_response("Situation", "specific_bellandur_query", canned)

    canned_res = adapter.generate(
        agent_name="Situation",
        prompt="specific_bellandur_query",
        schema=SampleExtractionSchema
    )
    assert canned_res.location_name == "Bellandur EcoSpace"
    assert canned_res.severity == 4
    assert canned_res.is_life_threatening is True


def test_llm_output_failing_schema_validation_is_rejected():
    """Test 3: LLM output that fails schema validation is rejected with ValidationError."""
    call_count = 0

    # Provider returning schema-violating data (severity is a string "high", violates int constraint)
    def malformed_provider_fn(agent: str, prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return '{"incident_type": "flood", "severity": "EXTREME_HIGH", "location_name": "Silk Board"}'

    adapter = LLMAdapter(mode=LLMMode.LIVE, live_provider_fn=malformed_provider_fn)

    # Attempting generation must trigger 1 initial attempt + 1 retry, then raise ValidationError
    with pytest.raises(ValidationError):
        adapter.generate(
            agent_name="Situation",
            prompt="Parse report",
            schema=SampleExtractionSchema,
            trace_id="trace-fail"
        )

    # Verified that it retried once before rejecting
    assert call_count == 2, f"Expected 2 attempts (initial + 1 retry), got {call_count}"
def test_replay_reproduces_a_recorded_run(tmp_path):
    """Test 4: Replay mode reproduces a recorded run from stored data or file."""
    adapter = LLMAdapter(mode=LLMMode.REPLAY)
    trace_id = "replay-trace-999"
    recorded_json = (
        '{"incident_type": "flood", "severity": 5, '
        '"location_name": "Outer Ring Road Underpass", "is_life_threatening": true}'
    )

    # Register in memory
    adapter.register_replay(trace_id, recorded_json)
    output = adapter.generate(
        agent_name="Situation",
        prompt="Arbitrary prompt in replay mode",
        schema=SampleExtractionSchema,
        trace_id=trace_id
    )
    assert output.severity == 5
    assert output.location_name == "Outer Ring Road Underpass"
    assert output.is_life_threatening is True

    # Test loading from file
    replay_file = tmp_path / "replay_data.json"
    import json
    with open(replay_file, "w", encoding="utf-8") as f:
        json.dump({"file-trace-1": recorded_json}, f)

    adapter_file = LLMAdapter(mode=LLMMode.REPLAY)
    adapter_file.load_replay_file(replay_file)
    output_file = adapter_file.generate(
        agent_name="Situation",
        prompt="Prompt",
        schema=SampleExtractionSchema,
        trace_id="file-trace-1"
    )
    assert output_file.location_name == "Outer Ring Road Underpass"
