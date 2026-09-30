"""Strict Pydantic v2 Domain Models for CrisisMesh.

All models enforce extra="forbid", strict type validation, and range limits.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    """Base model enforcing strict validation and forbidding undeclared fields."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# -------------------------------------------------------------------------
# Core Enums
# -------------------------------------------------------------------------

class VerificationLabel(str, Enum):
    """Status assigned by the Verification Engine."""
    CONFIRMED = "confirmed"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"


class UnitType(str, Enum):
    """Types of emergency response units."""
    AMBULANCE = "ambulance"
    RESCUE_TEAM = "rescue_team"
    SHELTER = "shelter"


class UnitStatus(str, Enum):
    """Operational status of a unit."""
    IDLE = "idle"
    EN_ROUTE = "en_route"
    UNAVAILABLE = "unavailable"


# -------------------------------------------------------------------------
# Incident & Report Models
# -------------------------------------------------------------------------

class Report(StrictBase):
    """Incoming untrusted citizen or agency report."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique report ID")
    text: str = Field(..., min_length=1, max_length=2000, description="Raw report text")
    source_id: str = Field(..., description="Identifier for reporting source")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Submission timestamp")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Reported latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Reported longitude")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata tags")


class IncidentRecord(StrictBase):
    """Structured incident extracted from untrusted reports by Situation Agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique incident ID")
    title: str = Field(..., min_length=1, max_length=200, description="Descriptive summary")
    description: str = Field(default="", max_length=2000, description="Detailed situation description")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Estimated incident latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Estimated incident longitude")
    severity: int = Field(default=3, ge=1, le=5, description="Severity rating 1 (lowest) to 5 (critical)")
    people_affected: int = Field(default=1, ge=0, description="Estimated number of victims or evacuees")
    required_unit_type: UnitType = Field(..., description="Type of resource needed")
    is_life_threatening: bool = Field(default=False, description="Flag for immediate mortality risk")
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Original report timestamp")
    extraction_confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="LLM extraction confidence")
    confidence: Optional[float] = Field(default=0.8, description="Legacy alias for extraction_confidence")
    ambiguous_fields: List[str] = Field(default_factory=list, description="Fields needing clarification")
    verification_label: VerificationLabel = Field(default=VerificationLabel.UNVERIFIED, description="Verification status")
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Deterministic credibility score")
    report_ids: List[str] = Field(default_factory=list, description="Raw report IDs linked to this incident")


class SensorReading(StrictBase):
    """Physical telemetry ground-truth reading (water level, rainfall)."""
    sensor_id: str = Field(..., description="Unique physical sensor ID")
    sensor_type: str = Field(..., description="Type of sensor e.g. water_level, rainfall")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Sensor latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Sensor longitude")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Reading timestamp")
    value: float = Field(..., description="Observed value")
    unit: str = Field(..., description="Measurement unit (e.g. meters, mm/hr)")
    flood_threshold: float = Field(default=0.5, description="Threshold above which flood is confirmed")
    coverage_radius_m: float = Field(default=1000.0, description="Geographic corroboration radius in meters")


# -------------------------------------------------------------------------
# Resource, Hospital & Shelter Models
# -------------------------------------------------------------------------

class Unit(StrictBase):
    """Emergency response unit: ambulance, rescue_team, or shelter."""
    id: str = Field(..., description="Unique unit identifier")
    name: str = Field(..., description="Human-readable callsign")
    unit_type: UnitType = Field(..., description="Resource capability category")
    capacity: int = Field(default=1, ge=1, description="Transport or shelter capacity")
    status: UnitStatus = Field(default=UnitStatus.IDLE, description="Current operational state")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Current latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Current longitude")
    current_target_id: Optional[str] = Field(default=None, description="Incident ID if en_route")


class Hospital(StrictBase):
    """Receiving trauma center / hospital for casualty transfer."""
    id: str = Field(..., description="Hospital ID")
    name: str = Field(..., description="Hospital name")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Hospital latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Hospital longitude")
    capacity_total: int = Field(..., ge=1, description="Total bed/trauma capacity")
    capacity_available: int = Field(..., ge=0, description="Available bed capacity")


# -------------------------------------------------------------------------
# Impact & Routing Models
# -------------------------------------------------------------------------

class ImpactReport(StrictBase):
    """Deterministic report produced by the Impact Engine."""
    flooded_roads: List[Tuple[str, str]] = Field(default_factory=list, description="Currently blocked road segments")
    unreachable_nodes: List[str] = Field(default_factory=list, description="Nodes disconnected from network")
    hard_to_reach_hospitals: List[str] = Field(default_factory=list, description="Hospitals with excessive delay")
    isolated_incidents: List[str] = Field(default_factory=list, description="Incidents cut off from fleet")
    travel_time_matrix: Dict[str, float] = Field(default_factory=dict, description="Keyed as 'unit_id:incident_id' -> minutes")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Evaluation timestamp")


class Veto(StrictBase):
    """Veto issued by Impact Agent against infeasible proposed assignments."""
    veto_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: str = Field(..., description="Reason for veto (e.g. route cut off by flood)")
    constraints: List[Tuple[str, str]] = Field(..., description="Infeasible (unit_id, incident_id) pairs")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# -------------------------------------------------------------------------
# Plan & Allocation Models
# -------------------------------------------------------------------------

class Assignment(StrictBase):
    """Assignment of an emergency unit to a specific incident."""
    unit_id: str = Field(..., description="Assigned unit ID")
    incident_id: str = Field(..., description="Target incident ID")
    eta_minutes: float = Field(..., ge=0.0, description="Estimated arrival time in minutes")
    is_provisional: bool = Field(default=False, description="Flag for provisional assignments on unverified incidents")
    requires_human_confirmation: bool = Field(default=False, description="Human confirmation requirement")
    target_hospital_id: Optional[str] = Field(default=None, description="Assigned destination hospital")
    cost: float = Field(default=0.0, ge=0.0, description="Computed assignment cost")


class RunnerUp(StrictBase):
    """Runner-up unit candidate for counterfactual explanations."""
    incident_id: str
    unit_id: Optional[str] = None
    delta_eta_minutes: float = 0.0
    delta_cost: float = 0.0
    reason_not_chosen: str = ""


class PlanCost(StrictBase):
    """Granular cost breakdown of the CP-SAT allocation objective."""
    total_cost: float = Field(ge=0.0)
    delay_harm_cost: float = Field(ge=0.0)
    wasted_dispatch_cost: float = Field(ge=0.0)
    switching_penalty_cost: float = Field(ge=0.0)
    unserved_penalty_cost: float = Field(ge=0.0)


class Plan(StrictBase):
    """Complete allocation plan produced by Resource Agent."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assignments: List[Assignment] = Field(default_factory=list)
    unserved_incidents: List[str] = Field(default_factory=list)
    cost_breakdown: PlanCost
    runner_up_per_incident: Dict[str, RunnerUp] = Field(default_factory=dict)
    status: str = Field(default="PROPOSED")  # PROPOSED, VETOED, APPROVED, REJECTED


class ChangeKind(str, Enum):
    """Classification of plan allocation modifications."""
    FORCED_UNIT_LOSS = "forced_unit_loss"
    OPTIMIZATION_REDIRECT = "optimization_redirect"
    NEW_ASSIGNMENT = "new_assignment"


class PlanChange(StrictBase):
    """Detailed change for a unit in a PlanDiff."""
    unit_id: str
    from_incident_id: Optional[str] = None
    to_incident_id: Optional[str] = None
    reason: str
    cost_delta: float
    change_kind: ChangeKind = ChangeKind.OPTIMIZATION_REDIRECT
    eta_before: Optional[float] = None
    eta_after: Optional[float] = None
    requires_human_decision: bool = False


class PlanDiff(StrictBase):
    """Delta comparison between previous approved plan and newly generated plan."""
    old_plan_id: Optional[str] = None
    new_plan_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changes: List[PlanChange] = Field(default_factory=list)
    total_cost_delta: float = 0.0
    units_redirected: int = 0
    requires_human_decision: bool = False
    summary: str = ""


# -------------------------------------------------------------------------
# Security & Message Models
# -------------------------------------------------------------------------

class Message(StrictBase):
    """Typed Message exchanged on the MessageBus."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = Field(..., description="Sending agent name")
    receiver: str = Field(..., description="Receiving agent name or *")
    type: str = Field(..., description="Typed message category")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary typed payload")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="End-to-end trace correlation ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityEvent(StrictBase):
    """Security audit event logged by Ingestion Gateway, BaseAgent, or Guardian."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(..., description="Category e.g. permission_violation, prompt_injection, spoofed_sensor")
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    agent_name: str = Field(..., description="Agent or module that detected the event")
    description: str = Field(..., description="Detailed description of the incident")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
