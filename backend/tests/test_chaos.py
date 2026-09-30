"""Chaos Engineering & Fault Tolerance Tests for CrisisMesh.
Validates resilience against LLM mid-flight failure, timeout simulation, and network partition.
"""

import json
from pathlib import Path
import pytest
from backend.app.agents.base.llm_adapter import LLMAdapter, LLMMode
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from pydantic import BaseModel

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "scenario.json"


def load_scenario():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


class SampleExtractionSchema(BaseModel):
    incident_type: str
    severity: str
    summary: str


def test_chaos_llm_crash_triggers_graceful_degradation():
    """Simulates an abrupt provider crash (e.g., 500 or sudden network cut) during LLM invocation."""
    def faulty_live_provider(agent_name: str, prompt: str) -> str:
        raise ConnectionResetError("CHAOS: Remote LLM provider closed TCP socket abruptly")

    adapter = LLMAdapter(mode=LLMMode.LIVE, live_provider_fn=faulty_live_provider)

    assert not adapter.is_degraded
    assert adapter.degraded_reason is None

    # Invocation should NOT crash; it should catch the failure and gracefully fall back to deterministic mock
    result = adapter.generate(
        agent_name="SituationAgent",
        prompt="A massive flash flood has stranded cars at Silk Board junction",
        schema=SampleExtractionSchema,
        trace_id="chaos-trace-001",
    )

    # Verify structured output was still synthesized
    assert isinstance(result, SampleExtractionSchema)
    assert adapter.is_degraded is True
    assert "ConnectionResetError" in adapter.degraded_reason


def test_chaos_llm_timeout_triggers_fallback():
    """Simulates an external API timeout exceeding the provider deadline."""
    def timing_out_provider(agent_name: str, prompt: str) -> str:
        raise TimeoutError("CHAOS: LLM HTTP request timed out after 5.0 seconds")

    adapter = LLMAdapter(mode=LLMMode.LIVE, live_provider_fn=timing_out_provider)

    result = adapter.generate(
        agent_name="VerificationAgent",
        prompt="Verify report from citizen regarding Bellandur lake overflow",
        schema=SampleExtractionSchema,
        trace_id="chaos-trace-002",
    )

    assert isinstance(result, SampleExtractionSchema)
    assert adapter.is_degraded is True
    assert "TimeoutError" in adapter.degraded_reason


def test_chaos_multi_agent_pipeline_survives_llm_death():
    """Simulates LLM death mid-run of the full 7-agent LangGraph orchestrator."""
    def crashing_provider(agent_name: str, prompt: str) -> str:
        raise RuntimeError(f"CHAOS: Fatal GPU out-of-memory on LLM host during {agent_name}")

    adapter = LLMAdapter(mode=LLMMode.LIVE, live_provider_fn=crashing_provider)
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus, llm_adapter=adapter)
    scenario = load_scenario()

    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {},
        "raw_reports": {
            "rep_chaos_01": {
                "id": "rep_chaos_01",
                "source_id": "citizen_99",
                "text": "Water rising rapidly near Silk Board underpass, cars stranded!",
                "lat": 12.9176,
                "lon": 77.6238,
                "timestamp": 0.0,
            }
        },
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    config = {"configurable": {"thread_id": "test-chaos-trace"}}
    final_state = orchestrator.graph.invoke(initial_state, config=config)

    # Verify system completed its execution without throwing unhandled exceptions
    assert final_state is not None
    assert orchestrator.llm.is_degraded is True
    assert "RuntimeError" in orchestrator.llm.degraded_reason
    # The CP-SAT solver and deterministic engines still produced an operational plan
    assert "current_plan" in final_state
    assert final_state["current_plan"] is not None
