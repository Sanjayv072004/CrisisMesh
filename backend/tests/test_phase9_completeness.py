import pytest
import os
from unittest.mock import MagicMock
from datetime import datetime, timezone
import math

from backend.app.agents.base.bus import MessageBus
from backend.app.models.schemas import Plan, PlanCost, Assignment, Unit, UnitType, UnitStatus, IncidentRecord, Hospital, VerificationLabel
from backend.app.engines.verification import credibility_score, cluster_duplicates
from backend.app.engines.allocation import AllocationEngine
from backend.app.audit.chain import AuditChain
from backend.app.security.crypto import CommanderKeyManager, ApprovalGate, SignedApproval
from backend.app.security.rbac import RBACManager, CommanderToken
from backend.app.orchestration.graph import CrisisMeshOrchestrator
from backend.app.agents.comm import CommAgent
from backend.app.agents.impact import ImpactAgent

@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    monkeypatch.setenv("CRISISMESH_DEMO_MODE", "true")

def test_comm_agent_generates_advisory():
    bus = MessageBus()
    agent = CommAgent(bus=bus)

    plan_cost = PlanCost(total_cost=10, delay_harm_cost=5, wasted_dispatch_cost=0, switching_penalty_cost=0, unserved_penalty_cost=5)
    plan = Plan(plan_id="plan-123", cost_breakdown=plan_cost, assignments=[
        Assignment(unit_id="u1", incident_id="i1", eta_minutes=15.0)
    ])

    incidents = {
        "i1": IncidentRecord(id="i1", title="Flood 1", lat=12.9, lon=77.6, severity=4, required_unit_type=UnitType.RESCUE_TEAM)
    }

    state = {
        "current_plan": plan.model_dump(),
        "incidents": {k: v.model_dump() for k, v in incidents.items()}
    }

    new_state = agent.run(state)
    assert "public_advisory" in new_state
    adv = new_state["public_advisory"]
    assert adv["title"] == "Public Advisory: 1 Incidents Reported"
    assert adv["severity_level"] == "HIGH"
    assert "Flood 1" in adv["affected_areas"]
    assert adv["estimated_response_minutes"] == 15.0

def test_comm_agent_sends_bus_message():
    bus = MessageBus()
    agent = CommAgent(bus=bus)

    plan_cost = PlanCost(total_cost=10, delay_harm_cost=5, wasted_dispatch_cost=0, switching_penalty_cost=0, unserved_penalty_cost=5)
    plan = Plan(plan_id="plan-123", cost_breakdown=plan_cost, assignments=[])

    state = {
        "current_plan": plan.model_dump(),
        "incidents": {"i1": {"id": "i1", "title": "Flood 1", "lat": 12.9, "lon": 77.6, "severity": 2, "required_unit_type": "ambulance"}}
    }

    agent.run(state)
    trace = bus.get_trace()
    adv_msgs = [m for m in trace if m.type == "PublicAdvisory"]
    assert len(adv_msgs) == 1
    assert adv_msgs[0].payload["severity_level"] == "LOW"

def test_hospital_reachability_wired_in_impact_agent():
    bus = MessageBus()
    agent = ImpactAgent(bus=bus)

    u = Unit(id="u1", name="A1", unit_type=UnitType.AMBULANCE, lat=12.9176, lon=77.6238)
    i = IncidentRecord(id="i1", title="F1", lat=12.9345, lon=77.6265, severity=4, required_unit_type=UnitType.AMBULANCE)
    h = Hospital(id="h1", name="H1", lat=12.9583, lon=77.6485, capacity_total=10, capacity_available=10)

    state = {
        "incidents": {"i1": i.model_dump()},
        "units": [u.model_dump()],
        "hospitals": [h.model_dump()]
    }

    new_state = agent.run(state)
    assert "hospital_reachability" in new_state
    assert isinstance(new_state["hospital_reachability"], list)

def test_bayesian_credibility_update_sensor_confirmation():
    from backend.app.models.incident import SensorReading, Report
    r1 = Report(id="r1", text="Flood", source_id="unverified_anonymous", timestamp=datetime.now(timezone.utc), lat=12.9, lon=77.6, claimed_type="ambulance")

    s = SensorReading(sensor_id="s1", sensor_type="water_level", lat=12.9, lon=77.6, timestamp=datetime.now(timezone.utc), value=1.0, unit="m", flood_threshold=0.5, coverage_radius_m=1000)

    score = credibility_score([r1], [s], {"unverified_anonymous": 0.25}, datetime.now(timezone.utc))
    assert score > 0.5

def test_bayesian_credibility_update_sensor_denial():
    from backend.app.models.incident import SensorReading, Report
    r1 = Report(id="r1", text="Flood", source_id="unverified_anonymous", timestamp=datetime.now(timezone.utc), lat=12.9, lon=77.6, claimed_type="ambulance")

    s = SensorReading(sensor_id="s1", sensor_type="water_level", lat=12.9, lon=77.6, timestamp=datetime.now(timezone.utc), value=0.01, unit="m", flood_threshold=0.5, coverage_radius_m=1000)

    score = credibility_score([r1], [s], {"unverified_anonymous": 0.25}, datetime.now(timezone.utc))
    assert score < 0.1

def test_runner_up_counterfactuals_populated():
    u1 = Unit(id="u1", name="U1", unit_type=UnitType.AMBULANCE, lat=12.9, lon=77.6)
    u2 = Unit(id="u2", name="U2", unit_type=UnitType.AMBULANCE, lat=12.91, lon=77.61)
    i1 = IncidentRecord(id="i1", title="I1", lat=12.9, lon=77.6, required_unit_type=UnitType.AMBULANCE, severity=3)

    eng = AllocationEngine()
    plan = eng.solve([i1], [u1, u2])

    assert "i1" in plan.runner_up_per_incident
    ru = plan.runner_up_per_incident["i1"]
    assert ru.unit_id is not None
    assert "Higher ETA" in ru.reason_not_chosen

def test_ed25519_sign_and_verify_approval():
    km = CommanderKeyManager()
    gate = ApprovalGate()

    plan_dict = {"assignments": [], "cost_breakdown": {}}
    plan_hash = gate.compute_plan_hash(plan_dict)

    signed = gate.sign_approval("p1", plan_hash, km.signing_key)

    valid, reason = gate.verify_before_dispatch(signed, plan_hash, km.get_public_key_hex())
    assert valid is True

    valid2, reason2 = gate.verify_before_dispatch(signed, plan_hash, km.get_public_key_hex())
    assert valid2 is False
    assert "Replay attack" in reason2

def test_audit_chain_persists_across_reload(tmp_path):
    log_file = tmp_path / "audit.jsonl"

    chain1 = AuditChain(log_path=log_file)
    chain1.append("EV1", "ACT1", {"foo": "bar"})
    chain1.append("EV2", "ACT1", {"baz": 1})

    assert chain1.verify_chain()[0] is True

    chain2 = AuditChain(log_path=log_file)
    assert len(chain2) == 3 # GENESIS + 2 entries
    assert chain2.verify_chain()[0] is True
    assert chain2.get_entries()[1].event_type == "EV1"

def test_supervisor_selective_replan_unit_status_change():
    from backend.app.agents.supervisor import SupervisorAgent
    bus = MessageBus()
    agent = SupervisorAgent(bus=bus)
    state = {"trigger_event_type": "unit_status_change"}
    new_state = agent.run(state)
    assert new_state["scheduled_agents"][0] == "Resource"
    assert "Situation" not in new_state["scheduled_agents"]

def test_full_pipeline_includes_comm_agent():
    orch = CrisisMeshOrchestrator()
    state = {
        "trigger_event_type": "new_report",
        "raw_reports": [{"id": "r1", "text": "Flood requiring ambulance", "source_id": "verified_volunteer_01", "timestamp": "2026-09-30T12:00:00Z", "lat": 12.9, "lon": 77.6}],
        "units": [Unit(id="u1", name="U1", unit_type=UnitType.AMBULANCE, lat=12.9, lon=77.6).model_dump()],
        "hospitals": [],
        "sensors": []
    }

    # Run the graph until the human_approval interrupt
    import asyncio

    thread = {"configurable": {"thread_id": "test_1"}}
    final_state = orch.graph.invoke(state, thread)

    # CommAgent should have run and populated public_advisory before human_approval
    assert "public_advisory" in final_state
    adv = final_state["public_advisory"]
    assert "Flood" in adv["title"] or "1 Incidents Reported" in adv["title"]
