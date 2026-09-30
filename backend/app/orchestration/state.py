"""Shared LangGraph Typed State Model for Crisis Coordination."""
from __future__ import annotations
from typing import Dict, List, Optional, Any, TypedDict
from pydantic import BaseModel, Field


from backend.app.models.schemas import Plan, PlanDiff


class DisasterState(TypedDict, total=False):
    """Shared typed state model for LangGraph workflow execution."""
    incidents: Dict[str, Any]
    raw_reports: Dict[str, Any]
    sensors: List[Dict[str, Any]]
    source_registry: Dict[str, float]
    units: List[Dict[str, Any]]
    hospitals: List[Dict[str, Any]]
    verification_labels: Dict[str, Any]
    impact_report: Optional[Dict[str, Any]]
    current_plan: Optional[Dict[str, Any]]
    previous_approved_plan: Optional[Dict[str, Any]]
    pending_approvals: List[Dict[str, Any]]
    message_log: List[Dict[str, Any]]
    negotiation_history: List[Dict[str, Any]]
    plan_diff: Optional[Dict[str, Any]]
    commander_briefing: Optional[Dict[str, Any]]
    active_agents: List[str]
    scheduled_agents: List[str]
    trigger_event_type: str
    pending_veto: Optional[Dict[str, Any]]
    veto_count: int
    step_budget: int
    audit_trail: List[Dict[str, Any]]
    status: str
    error: Optional[str]
    _clarification_loop_count: int
    commander_token: Optional[Any]
    signed_approval: Optional[Any]
    dispatch_error: Optional[str]


class StateSnapshot(BaseModel):
    """Pydantic model representation of the LangGraph state snapshot for APIs & UI."""
    incidents: Dict[str, Any] = Field(default_factory=dict)
    units: List[Dict[str, Any]] = Field(default_factory=list)
    hospitals: List[Dict[str, Any]] = Field(default_factory=list)
    verification_labels: Dict[str, Any] = Field(default_factory=dict)
    impact_report: Optional[Dict[str, Any]] = None
    current_plan: Optional[Plan] = None
    previous_approved_plan: Optional[Plan] = None
    plan_diff: Optional[PlanDiff] = None
    commander_briefing: Optional[Dict[str, Any]] = None
    pending_approvals: List[Dict[str, Any]] = Field(default_factory=list)
    message_log: List[Dict[str, Any]] = Field(default_factory=list)
    negotiation_history: List[Dict[str, Any]] = Field(default_factory=list)
    active_agents: List[str] = Field(default_factory=list)
    veto_count: int = 0
    step_budget: int = 20
    status: str = "INITIALIZED"
    dispatch_error: Optional[str] = None
