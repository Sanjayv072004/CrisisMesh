"""Comprehensive Tests for Phase 1B CP-SAT Allocation Engine."""
import json
from pathlib import Path
import pytest
from backend.app.engines.impact import ImpactEngine
from backend.app.engines.allocation import AllocationEngine, AllocationConfig
from backend.app.models.schemas import (
    Unit, UnitType, UnitStatus, IncidentRecord, VerificationLabel, Plan, PlanDiff
)

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "scenario.json"


def load_scenario():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def test_sensible_plan_for_t0_scenario(capsys):
    """Test 1: Sensible allocation plan for the 3-incident T0 scenario."""
    scenario = load_scenario()
    impact = ImpactEngine(force_synthetic=True)
    solver = AllocationEngine(AllocationConfig())

    units = [Unit(**u) for u in scenario["units"]]
    incidents = [IncidentRecord(**i) for i in scenario["t0_incidents"]]
    matrix = impact.travel_time_matrix(units, incidents)

    plan = solver.solve(incidents, units, matrix)

    assert len(plan.assignments) == 3, f"Expected all 3 T0 incidents served, got {len(plan.assignments)}"
    assert len(plan.unserved_incidents) == 0

    # Validate unit matching
    for a in plan.assignments:
        u = next(unit for unit in units if unit.id == a.unit_id)
        inc = next(i for i in incidents if i.id == a.incident_id)
        assert u.unit_type == inc.required_unit_type

    # Print T0 Plan for demonstration
    print("\n" + "="*60)
    print("=== T0 INITIAL ALLOCATION PLAN ===")
    print("="*60)
    for a in plan.assignments:
        prov = " [PROVISIONAL - Needs Human Confirmation]" if a.is_provisional else " [CONFIRMED]"
        print(f"-> {a.unit_id} assigned to {a.incident_id} | ETA: {a.eta_minutes} mins | Cost: {a.cost}{prov}")
    print("\n--- Cost Breakdown ---")
    print(f"Total Cost:            {plan.cost_breakdown.total_cost}")
    print(f"Delay Harm:            {plan.cost_breakdown.delay_harm_cost}")
    print(f"Wasted Dispatch:       {plan.cost_breakdown.wasted_dispatch_cost}")
    print(f"Switching Penalty:     {plan.cost_breakdown.switching_penalty_cost}")
    print(f"Unserved Penalty:      {plan.cost_breakdown.unserved_penalty_cost}")
    print("="*60 + "\n")


def test_unit_loss_and_critical_incident_changes_fewest_assignments_needed(capsys):
    """Test 2: Unit loss + critical incident at T+10 changes the fewest assignments needed."""
    scenario = load_scenario()
    impact = ImpactEngine(force_synthetic=True)
    solver = AllocationEngine(AllocationConfig(lambda_switch=75.0))

    units = [Unit(**u) for u in scenario["units"]]
    incidents = [IncidentRecord(**i) for i in scenario["t0_incidents"]]
    matrix_t0 = impact.travel_time_matrix(units, incidents)

    plan_t0 = solver.solve(incidents, units, matrix_t0)

    # T+10: amb_02 becomes unavailable, add critical underpass incident
    for u in units:
        if u.id == "amb_02":
            u.status = UnitStatus.UNAVAILABLE
        elif u.id in [a.unit_id for a in plan_t0.assignments]:
            u.status = UnitStatus.EN_ROUTE
            u.current_target_id = next(a.incident_id for a in plan_t0.assignments if a.unit_id == u.id)

    new_inc_data = scenario["t10_change_events"][0]["incident"]
    incidents.append(IncidentRecord(**new_inc_data))

    matrix_t10 = impact.travel_time_matrix(units, incidents)
    plan_t10 = solver.solve(incidents, units, matrix_t10, previous_plan=plan_t0)
    diff = solver.diff_plans(plan_t0, plan_t10)

    # Prints T+10 diff
    print("\n" + "="*60)
    print("=== T+10 REVISED PLAN DIFF ===")
    print("="*60)
    print(diff.summary)
    for c in diff.changes:
        dec = " [REQUIRES HUMAN DECISION]" if c.requires_human_decision else ""
        print(f"-> {c.unit_id}: {c.from_incident_id} -> {c.to_incident_id} | {c.reason}{dec}")
    print("="*60 + "\n")

    assert diff.units_redirected <= 1, "Switching penalty should prevent broad unnecessary fleet reshuffling"
    assert diff.requires_human_decision is True


def test_higher_lambda_reduces_reassignments():
    """Test 3: Higher switching penalty (lambda) prevents fleet churn."""
    scenario = load_scenario()
    impact = ImpactEngine(force_synthetic=True)

    units = [Unit(**u) for u in scenario["units"]]
    incidents = [IncidentRecord(**i) for i in scenario["t0_incidents"]]
    matrix = impact.travel_time_matrix(units, incidents)

    solver_low = AllocationEngine(AllocationConfig(lambda_switch=0.0))
    solver_high = AllocationEngine(AllocationConfig(lambda_switch=1000.0))

    plan_base = solver_low.solve(incidents, units, matrix)

    # Set all assigned units to EN_ROUTE
    for u in units:
        target = next((a.incident_id for a in plan_base.assignments if a.unit_id == u.id), None)
        if target:
            u.status = UnitStatus.EN_ROUTE
            u.current_target_id = target

    # Add a marginal incident
    incidents.append(IncidentRecord(
        id="inc_marginal",
        title="Minor waterlogging",
        lat=12.9180,
        lon=77.6240,
        severity=2,
        required_unit_type=UnitType.AMBULANCE,
        credibility_score=0.9
    ))
    matrix_new = impact.travel_time_matrix(units, incidents)

    plan_high = solver_high.solve(incidents, units, matrix_new, previous_plan=plan_base)
    diff_high = solver_high.diff_plans(plan_base, plan_high)

    assert diff_high.units_redirected == 0, "High lambda must strictly forbid redirecting active en-route units"


def test_unverified_incident_gets_provisional_assignment_only():
    """Test 4: Unverified incidents receive provisional assignments with confirmation flag."""
    scenario = load_scenario()
    impact = ImpactEngine(force_synthetic=True)
    solver = AllocationEngine(AllocationConfig())

    units = [Unit(**u) for u in scenario["units"]]
    incidents = [IncidentRecord(**i) for i in scenario["t0_incidents"]]
    matrix = impact.travel_time_matrix(units, incidents)

    plan = solver.solve(incidents, units, matrix)

    unverified_assignment = next(
        (a for a in plan.assignments if a.incident_id == "inc_t0_03"), None
    )
    assert unverified_assignment is not None
    assert unverified_assignment.is_provisional is True
    assert unverified_assignment.requires_human_confirmation is True


def test_demand_greater_than_supply_lists_unserved_incidents():
    """Test 5: When demand exceeds fleet capacity, solver lists unserved incidents."""
    impact = ImpactEngine(force_synthetic=True)
    solver = AllocationEngine(AllocationConfig())

    # Only 1 ambulance available
    units = [
        Unit(id="amb_lone", name="Lone Amb", unit_type=UnitType.AMBULANCE, status=UnitStatus.IDLE, lat=12.9176, lon=77.6238)
    ]
    # 3 ambulance incidents
    incidents = [
        IncidentRecord(id="inc_a", title="Cardiac 1", severity=5, lat=12.9176, lon=77.6238, required_unit_type=UnitType.AMBULANCE),
        IncidentRecord(id="inc_b", title="Trauma 2", severity=4, lat=12.9345, lon=77.6265, required_unit_type=UnitType.AMBULANCE),
        IncidentRecord(id="inc_c", title="Minor 3", severity=2, lat=12.9591, lon=77.6974, required_unit_type=UnitType.AMBULANCE),
    ]
    matrix = impact.travel_time_matrix(units, incidents)

    plan = solver.solve(incidents, units, matrix)

    assert len(plan.assignments) == 1
    assert plan.assignments[0].incident_id == "inc_a"  # Highest severity served
    assert set(plan.unserved_incidents) == {"inc_b", "inc_c"}
    assert plan.cost_breakdown.unserved_penalty_cost > 0


def test_robust_plan_worst_case_cost_le_naive_plan():
    """Test 6: Uncertainty-aware robust plan expected cost <= naive baseline cost under ambiguity."""
    impact = ImpactEngine(force_synthetic=True)
    
    # 1 ambulance, 1 confirmed critical incident, 1 unverified low-credibility incident
    units = [
        Unit(id="amb_1", name="Amb 1", unit_type=UnitType.AMBULANCE, status=UnitStatus.IDLE, lat=12.9176, lon=77.6238)
    ]
    incidents = [
        IncidentRecord(id="inc_real", title="Severe Trauma", severity=5, credibility_score=0.95, verification_label=VerificationLabel.CONFIRMED, lat=12.9180, lon=77.6240, required_unit_type=UnitType.AMBULANCE),
        IncidentRecord(id="inc_rumor", title="Unconfirmed Rumor", severity=5, credibility_score=0.20, verification_label=VerificationLabel.UNVERIFIED, lat=12.9176, lon=77.6238, required_unit_type=UnitType.AMBULANCE)
    ]
    matrix = impact.travel_time_matrix(units, incidents)

    solver_robust = AllocationEngine(AllocationConfig(is_naive_baseline=False))
    solver_naive = AllocationEngine(AllocationConfig(is_naive_baseline=True))

    plan_robust = solver_robust.solve(incidents, units, matrix)
    plan_naive = solver_naive.solve(incidents, units, matrix)

    # The robust plan prioritizes the confirmed real emergency over the 0.20 rumor
    assert plan_robust.assignments[0].incident_id == "inc_real"
    assert "inc_rumor" in plan_robust.unserved_incidents

    # The expected cost under uncertainty is lower in the robust optimization
    assert plan_robust.cost_breakdown.total_cost <= plan_naive.cost_breakdown.total_cost

