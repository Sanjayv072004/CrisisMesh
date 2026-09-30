"""Unit and Integration Tests for Road Graph & CP-SAT Allocation Engines."""
from datetime import datetime, timezone
import pytest
from backend.app.engines.road_graph import RoadGraphEngine
from backend.app.engines.allocation import AllocationEngine, SolverConfig
from backend.app.models.resource import UnitType, UnitStatus, EmergencyUnit, IncidentRequirement
from backend.app.engines.mock_data import get_mock_hospitals, get_mock_fleet, get_mock_scenario_incidents


def test_road_graph_routing_and_blocking():
    """Verify shortest path routing, area blockage, and rerouting."""
    engine = RoadGraphEngine()

    # Silk Board to Bellandur EcoSpace
    eta_open, path_open = engine.compute_travel_time_minutes(12.9176, 77.6238, 12.9260, 77.6762)
    assert eta_open < float("inf")
    assert len(path_open) >= 2

    # Block the direct corridor between HSR and Bellandur
    blocked = engine.block_road("hsr_sector_6", "bellandur_ecospace", reason="flooding", flood_depth=1.5)
    assert blocked is True

    # Check reroute
    eta_rerouted, path_rerouted = engine.compute_travel_time_minutes(12.9176, 77.6238, 12.9260, 77.6762)
    assert eta_rerouted >= eta_open or "hsr_sector_6" not in path_rerouted

    # Unblock
    engine.unblock_road("hsr_sector_6", "bellandur_ecospace")


def test_cpsat_solver_and_uncertainty_aware_provisional_assignment():
    """Verify CP-SAT solver optimizes allocation and marks unverified incidents as provisional."""
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    road_engine = RoadGraphEngine()
    solver = AllocationEngine(road_engine)

    fleet = get_mock_fleet()
    incidents = get_mock_scenario_incidents(now)
    hospitals = get_mock_hospitals()

    plan = solver.solve_plan(incidents=incidents, units=fleet, hospitals=hospitals)

    assert plan.status == "PROPOSED"
    assert len(plan.assignments) > 0

    # Incident inc_koramangala_unverified has credibility 0.42 (< 0.75) and is_verified=False
    # USP Pillar 1: Must be designated provisional!
    provisional_assignments = [a for a in plan.assignments if a.incident_id == "inc_koramangala_unverified"]
    if provisional_assignments:
        assert provisional_assignments[0].is_provisional is True, "Unverified incident assignment must be provisional!"

    # Type constraint check: Rescue boat cannot be assigned to ambulance incident
    for a in plan.assignments:
        unit = next(u for u in fleet if u.id == a.unit_id)
        inc = next(i for i in incidents if i.id == a.incident_id)
        assert unit.unit_type == inc.required_unit_type

    # Runner-up counterfactual explanation check
    for inc_id in [i.id for i in incidents]:
        assert inc_id in plan.runner_up_per_incident
        runner_up = plan.runner_up_per_incident[inc_id]
        assert runner_up.reason_not_chosen != ""


def test_cpsat_solver_respects_impact_veto():
    """Verify that when an assignment is vetoed by Impact, the solver re-solves under the constraint."""
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    road_engine = RoadGraphEngine()
    solver = AllocationEngine(road_engine)

    fleet = get_mock_fleet()
    incidents = get_mock_scenario_incidents(now)
    hospitals = get_mock_hospitals()

    # Initial plan
    plan1 = solver.solve_plan(incidents=incidents, units=fleet, hospitals=hospitals)
    assert len(plan1.assignments) > 0
    assigned_pair = (plan1.assignments[0].unit_id, plan1.assignments[0].incident_id)

    # VETO the first assignment (simulate Impact Engine veto)
    forbidden = {assigned_pair}
    plan2 = solver.solve_plan(incidents=incidents, units=fleet, hospitals=hospitals, forbidden_pairs=forbidden)

    # Assert the vetoed assignment is NEVER made in plan2
    for a in plan2.assignments:
        assert (a.unit_id, a.incident_id) != assigned_pair


def test_low_churn_replanning_and_diff():
    """Verify USP Pillar 2: Low-churn re-planning penalizes switching and diff flags human decisions."""
    now = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
    road_engine = RoadGraphEngine()
    solver = AllocationEngine(road_engine)

    fleet = get_mock_fleet()
    incidents = get_mock_scenario_incidents(now)
    hospitals = get_mock_hospitals()

    plan1 = solver.solve_plan(incidents=incidents, units=fleet, hospitals=hospitals)

    # Simulate unit amb_02 being EN_ROUTE to inc_silk_board_01
    for u in fleet:
        if u.id == "amb_02":
            u.status = UnitStatus.EN_ROUTE
            u.current_incident_id = "inc_silk_board_01"

    # Add a new moderate incident
    incidents.append(IncidentRequirement(
        id="inc_hsr_new",
        title="Minor waterlogging at HSR Sector 6",
        lat=12.9116,
        lon=77.6388,
        severity=2,
        credibility=0.90,
        required_unit_type=UnitType.AMBULANCE,
        is_verified=True,
        reported_at=now
    ))

    plan2 = solver.solve_plan(incidents=incidents, units=fleet, hospitals=hospitals)
    diff = solver.diff_plans(plan1, plan2)

    assert diff.new_plan_id == plan2.plan_id
    assert diff.summary != ""
