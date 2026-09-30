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
    expires_in_seconds: int = 86400


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
