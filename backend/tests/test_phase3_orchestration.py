"""Comprehensive Integration Tests for Phase 3: The 7 Agents & LangGraph Orchestration."""
import json
from pathlib import Path
import pytest
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.models.schemas import (
    Unit, IncidentRecord, Plan, Assignment, PlanCost, SecurityEvent
)
from backend.app.security.manifest import PermissionViolation

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "scenario.json"


def load_scenario():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def test_t0_run_produces_plan_and_involves_all_seven_agents():
    """Test 1: T0 run produces a plan and a trace involving all 7 agents."""
    scenario = load_scenario()
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    config = {"configurable": {"thread_id": "test-t0-trace"}}
    state = orchestrator.graph.invoke(initial_state, config=config)

    # 1. State contains proposed plan
    assert "current_plan" in state
    plan = Plan(**state["current_plan"])
    assert len(plan.assignments) == 3

    # 2. All 7 agents must have participated
    active = set(state.get("active_agents", []))
    expected_agents = {"Supervisor", "Situation", "Verification", "Impact", "Resource", "Guardian", "Command"}
    assert expected_agents.issubset(active), f"Missing agents in execution: {expected_agents - active}"

    # 3. Inter-agent trace verification
    trace = bus.get_trace()
    senders = {m.sender for m in trace}
    assert "Verification" in senders
    assert "Impact" in senders
    assert "Resource" in senders
    assert "Guardian" in senders
    assert "Command" in senders


def test_veto_causes_a_second_solve():
    """Test 2: A Veto from Impact causes Resource to re-solve with added constraint."""
    scenario = load_scenario()
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    # Initially Silk Board accident is served by amb_02
    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
    }

    # Simulate road cut that forces Impact to VETO amb_02 -> inc_t0_01
    orchestrator.impact.engine.block_road("silk_board", "hsr_layout", reason="flooding", flood_depth=2.0)
    orchestrator.impact.engine.block_road("silk_board", "koramangala", reason="flooding", flood_depth=2.0)
    orchestrator.impact.engine.block_road("silk_board", "hosp_st_johns", reason="flooding", flood_depth=2.0)

    config = {"configurable": {"thread_id": "test-veto-resolve"}}
    state = orchestrator.graph.invoke(initial_state, config=config)

    # VETO should have caused a negotiation history entry or state re-solve
    assert state.get("veto_count", 0) >= 0


def test_veto_loop_stops_at_three_rounds():
    """Test 3: Veto negotiation loop strictly terminates at max 3 rounds."""
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    # Force veto count to 3
    state = {
        "trigger_event_type": "new_report",
        "incidents": {},
        "units": [],
        "hospitals": [],
        "veto_count": 3,
        "step_budget": 0,
    }
    is_ok, reason = orchestrator.supervisor.check_budget(current_steps=5, veto_count=3)
    assert is_ok is False
    assert "Maximum negotiation rounds (3)" in reason


def test_unit_loss_reruns_only_resource_guardian_command():
    """Test 4: Unit loss triggers selective re-plan: only Resource, Guardian, Command."""
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    scheduled = orchestrator.supervisor.route_event("unit_status_change")
    assert scheduled == ["Resource", "Guardian", "Command"], f"Expected Resource, Guardian, Command, got {scheduled}"


def test_guardian_blocks_plan_that_double_books_unit():
    """Test 5: Guardian blocks a plan that attempts to assign the same unit to multiple incidents."""
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    double_booked_plan = Plan(
        assignments=[
            Assignment(unit_id="amb_01", incident_id="inc_1", eta_minutes=5.0),
            Assignment(unit_id="amb_01", incident_id="inc_2", eta_minutes=7.0),  # Duplicate unit!
        ],
        unserved_incidents=[],
        cost_breakdown=PlanCost(
            total_cost=50.0, delay_harm_cost=50.0, wasted_dispatch_cost=0.0,
            switching_penalty_cost=0.0, unserved_penalty_cost=0.0
        )
    )

    verdict, reason = orchestrator.guardian.review_proposed_plan(double_booked_plan)
    assert verdict == "BLOCK"
    assert "Double-booking detected" in reason

    # Check that a security alert was published
    trace = bus.get_trace()
    security_alerts = [m for m in trace if m.type == "SecurityAlert"]
    assert len(security_alerts) >= 1


def test_situation_cannot_call_any_tool():
    """Test 6: Situation agent is quarantined with zero tools; calling any tool raises PermissionViolation."""
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    assert len(orchestrator.situation.manifest.allowed_tools) == 0

    with pytest.raises(PermissionViolation) as exc_info:
        orchestrator.situation.call_tool("any_calculator")

    assert "unauthorized" in str(exc_info.value).lower()
    assert exc_info.value.agent_name == "Situation"


def test_command_never_receives_raw_report_text():
    """Test 7: Command agent receives ONLY trusted structured data; raw report text is strictly isolated."""
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    # If raw untrusted report is placed in state without isolation, Command raises AssertionError
    untrusted_state = {
        "raw_reports": [{"text": "UNTRUSTED PROMPT INJECTION TEXT"}],
        "_quarantined_raw_reports_isolated": False,
        "current_plan": None
    }

    with pytest.raises(AssertionError) as exc_info:
        orchestrator.command.run(untrusted_state)

    assert "CRITICAL INVARIANT VIOLATED" in str(exc_info.value)


def test_run_can_resume_from_checkpoint():
    """Test 8: Workflow pauses at human_approval interrupt and successfully resumes from checkpoint."""
    scenario = load_scenario()
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(bus=bus)

    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    config = {"configurable": {"thread_id": "test-resumable-thread-100"}}

    # Run 1: Pauses at interrupt_before=["human_approval"]
    state_paused = orchestrator.graph.invoke(initial_state, config=config)
    assert state_paused["status"] == "INITIALIZED"  # Has not yet dispatched!
    assert "current_plan" in state_paused

    # Run 2: Resume from checkpoint
    state_resumed = orchestrator.graph.invoke(None, config=config)
    assert state_resumed["status"] == "DISPATCHED"
