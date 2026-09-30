"""Pydantic v2 Schemas for FastAPI REST & WebSocket Endpoints."""
from __future__ import annotations
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from backend.app.security.rbac import Role


# -------------------------------------------------------------------------
# Authentication Schemas
# -------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[Role] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    public_key_hex: Optional[str] = None
    expires_in_seconds: int = 7200


# -------------------------------------------------------------------------
# Ingestion & Operational Schemas
# -------------------------------------------------------------------------
class ReportIngestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_id: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    ip_address: str = "127.0.0.1"


class ReportIngestResponse(BaseModel):
    report_id: Optional[str]
    status: str
    is_quarantined: bool
    confidence: float
    security_events: List[Dict[str, Any]] = Field(default_factory=list)


class SensorIngestRequest(BaseModel):
    sensor_id: str
    sensor_type: str = "water_level"
    lat: float
    lon: float
    value: float
    unit: str = "meters"
    flood_threshold: float = 0.5
    signature_hex: str


class UnitStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Operational state: idle, en_route, unavailable")
    current_target_id: Optional[str] = None


class RoadBlockRequest(BaseModel):
    u: Optional[str] = None
    v: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: Optional[float] = None


# -------------------------------------------------------------------------
# Plan Approval & Rejection Schemas
# -------------------------------------------------------------------------
class PlanApproveRequest(BaseModel):
    plan_hash: Optional[str] = None
    signature_hex: Optional[str] = None
    nonce: Optional[str] = None
    timestamp: Optional[float] = None
    decisions: Optional[Dict[str, bool]] = None
    auto_sign: bool = False  # Allows certified commander key from vault to auto-sign in dev mode


class PlanRejectRequest(BaseModel):
    reason: str
    forbidden_pairs: Optional[List[Tuple[str, str]]] = None


# -------------------------------------------------------------------------
# WebSocket Event Schema
# -------------------------------------------------------------------------
class WSEvent(BaseModel):
    """Typed WebSocket event streamed to frontend clients."""
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    type: str = Field(
        ...,
        description=(
            "Event type: agent_message, incident_updated, impact_updated, "
            "plan_proposed, plan_diff, approval_required, plan_approved, "
            "dispatch_issued, security_event, audit_status, scenario_status"
        ),
    )
    timestamp: float = Field(default_factory=time.time)
    trace_id: str = Field(default_factory=lambda: f"trace-{uuid.uuid4().hex[:8]}")
    payload: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# Attack & Scenario Schemas
# -------------------------------------------------------------------------
class AttackRequest(BaseModel):
    payload: Optional[Dict[str, Any]] = None


class AttackResponse(BaseModel):
    attack_type: str
    result: str  # BLOCKED, QUARANTINED, DETECTED
    mitigating_layer: str
    detail: str
    security_event: Optional[Dict[str, Any]] = None


class ScenarioPlayRequest(BaseModel):
    speed: float = Field(default=1.0, ge=0.1, le=10.0)


class HealthResponse(BaseModel):
    status: str
    version: str
    mode: str
    uptime_seconds: float
    timestamp: float


# -------------------------------------------------------------------------
# Phase 7 USP Proof & Analysis Schemas
# -------------------------------------------------------------------------
class LowChurnProofComparison(BaseModel):
    naive_units_redirected: int
    low_churn_units_redirected: int
    naive_total_cost: float
    low_churn_total_cost: float
    naive_delay_cost: float
    low_churn_delay_cost: float
    naive_switching_cost: float
    low_churn_switching_cost: float
    naive_wasted_cost: float = 0.0
    low_churn_wasted_cost: float = 0.0
    naive_unserved_cost: float = 0.0
    low_churn_unserved_cost: float = 0.0
    explanation: str


class UncertaintyProofComparison(BaseModel):
    incident_id: str
    incident_title: str
    credibility_score: float
    verification_label: str
    cost_if_true_naive: float
    cost_if_true_robust: float
    cost_if_false_naive: float
    cost_if_false_robust: float
    worst_case_naive: float
    worst_case_robust: float
    is_robust_le_naive: bool
    explanation: str


class CounterfactualExplanation(BaseModel):
    incident_id: str
    incident_title: str
    assigned_unit_id: str
    assigned_unit_type: str
    assigned_eta_minutes: float
    assigned_cost: float
    runner_up_unit_id: str
    runner_up_eta_minutes: float
    runner_up_cost: float
    delta_eta_minutes: float
    delta_cost: float
    rationale: str


class USPProofResponse(BaseModel):
    timestamp: float
    scenario_stage: str
    low_churn: LowChurnProofComparison
    uncertainty_aware: UncertaintyProofComparison
    counterfactual: CounterfactualExplanation

