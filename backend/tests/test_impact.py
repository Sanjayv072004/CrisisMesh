"""Tests for Phase 1A: Impact Engine, Road Blocking, Cut-off Detection, and Synthetic Fallback."""
import math
import pytest
from backend.app.engines.impact import ImpactEngine
from backend.app.models.schemas import Unit, UnitType, UnitStatus, IncidentRecord, Hospital


def test_blocking_road_increases_travel_time():
    """Verify that blocking an arterial road segment increases travel time or forces reroute."""
    engine = ImpactEngine(force_synthetic=True)

    # Travel from Silk Board (12.9176, 77.6238) to Bellandur (12.9260, 77.6762)
    t_open, path_open = engine.compute_travel_time(12.9176, 77.6238, 12.9260, 77.6762)
    assert t_open < float("inf")
    assert len(path_open) >= 2

    # Block direct link between HSR and Bellandur
    blocked = engine.block_road("hsr_layout", "bellandur", reason="flooding", flood_depth=1.5)
    assert blocked is True

    # Rerouted travel time
    t_reroute, path_reroute = engine.compute_travel_time(12.9176, 77.6238, 12.9260, 77.6762)
    assert t_reroute >= t_open or "hsr_layout" not in path_reroute


def test_cutoff_node_reported_unreachable():
    """Verify that when all incoming edges to an area are submerged, it is reported unreachable (inf)."""
    engine = ImpactEngine(force_synthetic=True)

    # Koramangala is connected to: silk_board, hosp_st_johns, hosp_manipal, bellandur
    engine.block_road("silk_board", "koramangala")
    engine.block_road("koramangala", "hosp_st_johns")
    engine.block_road("koramangala", "hosp_manipal")
    engine.block_road("koramangala", "bellandur")

    t_blocked, path = engine.compute_travel_time(12.9176, 77.6238, 12.9345, 77.6265)
    assert math.isinf(t_blocked), f"Expected inf travel time to cut-off node, got {t_blocked}"
    assert path == []


def test_synthetic_fallback_works_with_no_network():
    """Verify that synthetic fallback produces a fully connected, valid graph offline."""
    engine = ImpactEngine(force_synthetic=True)
    assert engine.graph is not None
    assert engine.graph.number_of_nodes() >= 8
    assert engine.graph.number_of_edges() >= 10

    # Ensure all key nodes exist
    nodes = set(engine.graph.nodes())
    assert "silk_board" in nodes
    assert "bellandur" in nodes
    assert "koramangala" in nodes
    assert "orr_underpass" in nodes
    assert "marathahalli" in nodes

    # Matrix generation works
    units = [
        Unit(id="u1", name="Amb 1", unit_type=UnitType.AMBULANCE, lat=12.9176, lon=77.6238),
        Unit(id="u2", name="Boat 1", unit_type=UnitType.RESCUE_TEAM, lat=12.9260, lon=77.6762)
    ]
    incidents = [
        IncidentRecord(id="inc1", title="Flood 1", lat=12.9345, lon=77.6265, required_unit_type=UnitType.AMBULANCE),
        IncidentRecord(id="inc2", title="Flood 2", lat=12.9591, lon=77.6974, required_unit_type=UnitType.RESCUE_TEAM)
    ]
    matrix = engine.travel_time_matrix(units, incidents)
    assert len(matrix) == 4
    for (u_id, inc_id), eta in matrix.items():
        assert eta > 0.0 and not math.isinf(eta)
