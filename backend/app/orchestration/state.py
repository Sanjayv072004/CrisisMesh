"""Shared LangGraph Typed State Model for Crisis Coordination."""
from __future__ import annotations
from typing import Dict, List, Optional, Any, TypedDict
from pydantic import BaseModel, Field


class DisasterState(TypedDict, total=False):
    """Shared typed state model for LangGraph workflow execution."""
    incidents: Dict[str, Any]
    verification_labels: Dict[str, Any]
    impact_report: Optional[Dict[str, Any]]
    current_plan: Optional[Dict[str, Any]]
    previous_approved_plan: Optional[Dict[str, Any]]
    pending_approvals: List[Dict[str, Any]]
    message_log: List[Dict[str, Any]]
    active_agents: List[str]
    veto_count: int
    step_budget: int
    audit_trail: List[Dict[str, Any]]
    status: str
    error: Optional[str]


class StateSnapshot(BaseModel):
    """Pydantic model representation of the LangGraph state snapshot for APIs & UI."""
    incidents: Dict[str, Any] = Field(default_factory=dict)
    verification_labels: Dict[str, Any] = Field(default_factory=dict)
    impact_report: Optional[Dict[str, Any]] = None
    current_plan: Optional[Dict[str, Any]] = None
    previous_approved_plan: Optional[Dict[str, Any]] = None
    pending_approvals: List[Dict[str, Any]] = Field(default_factory=list)
    message_log: List[Dict[str, Any]] = Field(default_factory=list)
    active_agents: List[str] = Field(default_factory=list)
    veto_count: int = 0
    step_budget: int = 20
    status: str = "INITIALIZED"
