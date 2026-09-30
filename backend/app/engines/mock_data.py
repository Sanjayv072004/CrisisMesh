"""Mock Scenario & Sensor Data Generator for Bengaluru Flood Crisis Demo."""
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from backend.app.models.resource import (
    EmergencyUnit, UnitType, UnitStatus, Hospital, IncidentRequirement
)
from backend.app.models.incident import SensorReading


def get_mock_hospitals() -> List[Hospital]:
    """Ground truth hospitals in South-East Bengaluru."""
    return [
        Hospital(
            id="hosp_st_johns",
            name="St. John's Medical College Hospital",
            lat=12.9312,
            lon=77.6202,
            capacity_total=100,
            capacity_available=25
        ),
        Hospital(
            id="hosp_sakra",
            name="Sakra World Hospital (Bellandur)",
            lat=12.9285,
            lon=77.6842,
            capacity_total=60,
            capacity_available=12
        ),
        Hospital(
            id="hosp_manipal",
            name="Manipal Hospital (Old Airport Road)",
            lat=12.9583,
            lon=77.6485,
            capacity_total=80,
            capacity_available=18
        ),
    ]


def get_mock_fleet() -> List[EmergencyUnit]:
    """Emergency fleet deployed across South-East Bengaluru."""
    return [
        EmergencyUnit(
            id="amb_01",
            name="108 Ambulance - Koramangala Base",
            unit_type=UnitType.AMBULANCE,
            status=UnitStatus.AVAILABLE,
            lat=12.9340,
            lon=77.6250,
            capacity=1
        ),
        EmergencyUnit(
            id="amb_02",
            name="108 Ambulance - Silk Board Depot",
            unit_type=UnitType.AMBULANCE,
            status=UnitStatus.AVAILABLE,
            lat=12.9180,
            lon=77.6245,
            capacity=1
        ),
        EmergencyUnit(
            id="amb_03",
            name="108 Ambulance - Marathahalli Station",
            unit_type=UnitType.AMBULANCE,
            status=UnitStatus.AVAILABLE,
            lat=12.9580,
            lon=77.6960,
            capacity=1
        ),
        EmergencyUnit(
            id="boat_01",
            name="SDRF Inflatable Boat - Bellandur Outpost",
            unit_type=UnitType.RESCUE_BOAT,
            status=UnitStatus.AVAILABLE,
            lat=12.9270,
            lon=77.6750,
            capacity=6
        ),
        EmergencyUnit(
            id="ndrf_01",
            name="NDRF Pumping & Rescue Squad - HSR",
            unit_type=UnitType.NDRF_SQUAD,
            status=UnitStatus.AVAILABLE,
            lat=12.9120,
            lon=77.6390,
            capacity=10
        ),
    ]


def get_mock_scenario_incidents(now: datetime) -> List[IncidentRequirement]:
    """Initial synthetic disaster scenario incidents."""
    return [
        IncidentRequirement(
            id="inc_silk_board_01",
            title="Submerged Car with Family at Silk Board Underpass",
            lat=12.9176,
            lon=77.6238,
            severity=5,
            credibility=0.92,
            required_unit_type=UnitType.AMBULANCE,
            is_verified=True,
            reported_at=now - timedelta(minutes=8)
        ),
        IncidentRequirement(
            id="inc_bellandur_01",
            title="Severe Water Inundation near EcoSpace Bellandur",
            lat=12.9260,
            lon=77.6762,
            severity=4,
            credibility=0.88,
            required_unit_type=UnitType.RESCUE_BOAT,
            is_verified=True,
            reported_at=now - timedelta(minutes=15)
        ),
        IncidentRequirement(
            id="inc_koramangala_unverified",
            title="Unconfirmed Report of Wall Collapse at Koramangala 4th Block",
            lat=12.9345,
            lon=77.6265,
            severity=3,
            credibility=0.42,
            required_unit_type=UnitType.AMBULANCE,
            is_verified=False,  # Unverified -> Should get provisional assignment
            reported_at=now - timedelta(minutes=4)
        ),
    ]
