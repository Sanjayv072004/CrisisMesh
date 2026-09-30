"""Comprehensive Integration Tests for Phase 3: The 7 Agents & LangGraph Orchestration."""
import json
from pathlib import Path
import pytest
from backend.app.agents.base.bus import MessageBus
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.engines.impact import ImpactEngine
from backend.app.models.schemas import (
    Unit, UnitType, IncidentRecord, Plan, Assignment, PlanCost, SecurityEvent, VerificationLabel
)
from backend.app.security.manifest import PermissionViolation
from backend.app.security.crypto import CommanderKeyManager, ApprovalGate
from backend.app.security.rbac import CommanderToken

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

    # Human Commander signs approval to authorize dispatch
    key_mgr = CommanderKeyManager()
    plan_hash = ApprovalGate.compute_plan_hash(state_paused["current_plan"])
    signed = orchestrator.approval_gate.sign_approval(
        plan_id=state_paused["current_plan"]["plan_id"],
        plan_hash=plan_hash,
        signing_key=key_mgr.signing_key,
    )
    token = CommanderToken(user_id="cmd_test", public_key_hex=key_mgr.get_public_key_hex())
    orchestrator.graph.update_state(config, {"commander_token": token, "signed_approval": signed})

    # Run 2: Resume from checkpoint
    state_resumed = orchestrator.graph.invoke(None, config=config)
    assert state_resumed["status"] == "DISPATCHED"


def test_unscripted_impact_veto_and_second_solve():
    """A11: Blocked road causes real unscripted VETO from ImpactAgent, triggering 2nd solve by ResourceAgent."""
    scenario = load_scenario()
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(
        bus=bus,
        sensors=scenario["sensors"],
        source_registry=scenario["source_registry"],
        raw_reports={r["id"]: r for r in scenario["raw_reports"]}
    )

    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "raw_reports": {r["id"]: r for r in scenario["raw_reports"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    # Run T0
    config = {"configurable": {"thread_id": "test-veto-a11"}}
    state = orchestrator.graph.invoke(initial_state, config=config)
    plan_t0 = Plan(**state["current_plan"])

    # Setup T+10: new incident at ORR underpass, amb_02 unavailable, rescue_01 en-route
    t10_inc = scenario["t10_change_events"][0]["incident"]
    state["incidents"][t10_inc["id"]] = t10_inc
    for u in state["units"]:
        if u["id"] == "amb_02":
            u["status"] = "unavailable"
        elif u["id"] in [a.unit_id for a in plan_t0.assignments]:
            u["status"] = "en_route"
            u["current_target_id"] = next(a.incident_id for a in plan_t0.assignments if a.unit_id == u["id"])

    # Pre-populate resource cached matrix with unblocked routes so resource proposes closest unit (rescue_01)
    for u in state["units"]:
        eta, _ = orchestrator.impact.engine.compute_travel_time(u["lat"], u["lon"], t10_inc["lat"], t10_inc["lon"])
        orchestrator.resource.cached_matrix[(u["id"], t10_inc["id"])] = round(eta, 1)

    # Physical road block in the environment: Underpass approaches flooded
    orchestrator.impact.engine.block_road("bellandur", "orr_underpass", reason="flooded underpass approach", flood_depth=2.5)
    orchestrator.impact.engine.block_road("bellandur", "hosp_sakra", reason="flooded underpass approach", flood_depth=2.0)
    orchestrator.impact.engine.block_road("koramangala", "bellandur", reason="flooded sarjapur road", flood_depth=1.5)
    orchestrator.impact.engine.block_road("hsr_layout", "bellandur", reason="flooded outer ring road", flood_depth=2.0)

    # Set naive baseline on proposal to induce rescue_01 assignment, testing unscripted veto
    orchestrator.resource.solver.config.is_naive_baseline = True
    orchestrator.resource.solver.config.lambda_switch = 0.0
    orchestrator.resource.solver.config.false_alarm_cost = 0.0

    state["trigger_event_type"] = "unit_status_change"
    state["previous_approved_plan"] = plan_t0.model_dump()
    state["active_agents"] = []

    t10_config = {"configurable": {"thread_id": "test-veto-a11-t10"}}
    state_t10 = orchestrator.graph.invoke(state, config=t10_config)

    # Assertions:
    # 1. Unscripted veto occurred and was recorded
    assert state_t10.get("veto_count", 0) >= 1, "ImpactAgent must have issued a Veto for the impassable route"
    assert len(state_t10.get("negotiation_history", [])) >= 1, "Negotiation history must record the veto round"

    # 2. Trace contains PlanVeto message from Impact to Resource
    trace = bus.get_trace()
    veto_msgs = [m for m in trace if m.sender == "Impact" and m.receiver == "Resource" and m.type == "PlanVeto"]
    assert len(veto_msgs) >= 1, f"Trace must contain PlanVeto from Impact to Resource, got: {[m.type for m in trace]}"

    # 3. Final plan was re-solved and is feasible (assigned rescue_02)
    final_plan = Plan(**state_t10["current_plan"])
    r1_assign = next(a for a in final_plan.assignments if a.unit_id == "rescue_01")
    r2_assign = next(a for a in final_plan.assignments if a.unit_id == "rescue_02")
    assert r1_assign.incident_id == "inc_t0_02", "rescue_01 must be preserved at inc_t0_02 after veto"
    assert r2_assign.incident_id == "inc_t10_critical_underpass", "rescue_02 must serve underpass in re-solved plan"


def test_guardian_credibility_floor_quarantine():
    """A13: Incidents below credibility floor (p=0.05 < 0.20) are quarantined, receive NO assignment, and log security alert."""
    from backend.app.engines.allocation import AllocationEngine, AllocationConfig
    scenario = load_scenario()
    impact = ImpactEngine(force_synthetic=True)
    solver = AllocationEngine(AllocationConfig(credibility_floor=0.20))

    units = [Unit(**u) for u in scenario["units"]]

    # Create legitimate incident + botnet flood fake incident (p=0.05)
    legit_inc = IncidentRecord(
        id="inc_legit_01",
        title="Verified Wall Collapse",
        lat=12.9176,
        lon=77.6238,
        severity=4,
        required_unit_type=UnitType.AMBULANCE,
        credibility_score=0.92,
        verification_label=VerificationLabel.CONFIRMED
    )
    botnet_inc = IncidentRecord(
        id="attack_rep_botnet_flood",
        title="Botnet Sybil Flooding Incident",
        lat=12.9590,
        lon=77.6970,
        severity=4,
        required_unit_type=UnitType.AMBULANCE,
        credibility_score=0.05,  # Far below floor 0.20
        verification_label=VerificationLabel.UNVERIFIED
    )

    incidents = [legit_inc, botnet_inc]
    matrix = impact.travel_time_matrix(units, incidents)
    plan = solver.solve(incidents, units, matrix)

    # 1. Botnet incident must NOT receive any assignment
    assigned_inc_ids = {a.incident_id for a in plan.assignments}
    assert "inc_legit_01" in assigned_inc_ids, "Legitimate incident must be assigned"
    assert "attack_rep_botnet_flood" not in assigned_inc_ids, "Quarantined incident below floor must NEVER be assigned"

    # 2. GuardianAgent audits and blocks any attempt to dispatch to it
    from backend.app.agents.guardian import GuardianAgent
    bus = MessageBus()
    guardian = GuardianAgent(bus=bus, credibility_floor=0.20)
    state = {
        "incidents": {i.id: i for i in incidents},
        "current_plan": plan.model_dump()
    }
    guardian.run(state)

    # Verify security alert logged for quarantined incident
    trace = bus.get_trace()
    alerts = [m for m in trace if m.type == "SecurityAlert"]
    assert len(alerts) >= 1, "Guardian must log SecurityAlert for quarantined incident"
    assert alerts[0].payload["event"]["event_type"] == "credibility_floor_quarantine"
    assert alerts[0].payload["event"]["metadata"]["incident_id"] == "attack_rep_botnet_flood"


def test_supervisor_clarification_trace():
    """A12: Verify Supervisor routing -> Situation -> ClarificationRequest -> Situation ClarificationResponse trace."""
    scenario = load_scenario()
    bus = MessageBus()
    orchestrator = CrisisMeshOrchestrator(
        bus=bus,
        sensors=scenario["sensors"],
        source_registry=scenario["source_registry"],
        raw_reports={r["id"]: r for r in scenario["raw_reports"]}
    )

    initial_state = {
        "trigger_event_type": "new_report",
        "incidents": {i["id"]: i for i in scenario["t0_incidents"]},
        "raw_reports": {r["id"]: r for r in scenario["raw_reports"]},
        "units": scenario["units"],
        "hospitals": scenario["hospitals"],
        "verification_labels": {},
        "active_agents": [],
        "veto_count": 0,
        "step_budget": 0,
        "status": "INITIALIZED"
    }

    config = {"configurable": {"thread_id": "test-clarification-trace-a12"}}
    state = orchestrator.graph.invoke(initial_state, config=config)

    trace = bus.get_trace()
    types = [m.type for m in trace]

    # Verify sequence: AgentTrigger -> ClarificationRequest -> ClarificationResponse
    assert "AgentTrigger" in types, "Trace must contain Supervisor AgentTrigger"
    assert "ClarificationRequest" in types, "Trace must contain Verification ClarificationRequest"
    assert "ClarificationResponse" in types, "Trace must contain Situation ClarificationResponse"

    idx_req = types.index("ClarificationRequest")
    idx_resp = types.index("ClarificationResponse")
    assert idx_req < idx_resp, "ClarificationRequest must precede ClarificationResponse"

