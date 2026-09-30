"""Domain Models for Units, Allocation Plans, and Plan Diffs."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class UnitType(str, Enum):
    AMBULANCE = "AMBULANCE"
    RESCUE_BOAT = "RESCUE_BOAT"
    FIRE_TRUCK = "FIRE_TRUCK"
    NDRF_SQUAD = "NDRF_SQUAD"


class UnitStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    EN_ROUTE = "EN_ROUTE"
    BUSY = "BUSY"
    MAINTENANCE = "MAINTENANCE"


class EmergencyUnit(BaseModel):
    id: str
    name: str
    unit_type: UnitType
    status: UnitStatus = UnitStatus.AVAILABLE
    lat: float
    lon: float
    capacity: int = 1
    current_incident_id: Optional[str] = None  # If already EN_ROUTE or BUSY


class Hospital(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    capacity_total: int
    capacity_available: int


class IncidentRequirement(BaseModel):
    id: str
    title: str
    lat: float
    lon: float
    severity: int = Field(ge=1, le=5)
    credibility: float = Field(ge=0.0, le=1.0)
    required_unit_type: UnitType
    is_verified: bool = False
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UnitAssignment(BaseModel):
    unit_id: str
    incident_id: str
    eta_minutes: float
    is_provisional: bool = False
    target_hospital_id: Optional[str] = None
    cost: float = 0.0


class RunnerUpOption(BaseModel):
    incident_id: str
    runner_up_unit_id: Optional[str] = None
    delta_eta_minutes: float = 0.0
    delta_cost: float = 0.0
    reason_not_chosen: str = ""


class PlanCostBreakdown(BaseModel):
    total_cost: float
    delay_harm_cost: float
    wasted_dispatch_cost: float
    switching_penalty_cost: float
    unserved_penalty_cost: float


class PlanProposal(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assignments: List[UnitAssignment] = Field(default_factory=list)
    unserved_incidents: List[str] = Field(default_factory=list)
    cost_breakdown: PlanCostBreakdown
    runner_up_per_incident: Dict[str, RunnerUpOption] = Field(default_factory=dict)
    status: str = "PROPOSED"  # PROPOSED, VETOED, APPROVED, REJECTED


class PlanChangeDetail(BaseModel):
    unit_id: str
    previous_incident_id: Optional[str]
    new_incident_id: Optional[str]
    reason: str
    cost_delta: float
    requires_human_decision: bool = False


class PlanDiff(BaseModel):
    old_plan_id: Optional[str]
    new_plan_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changes: List[PlanChangeDetail] = Field(default_factory=list)
    total_cost_delta: float = 0.0
    units_redirected: int = 0
    requires_human_decision: bool = False
    summary: str = ""
