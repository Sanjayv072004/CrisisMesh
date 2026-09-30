"""Scenario Control API Routes: Reset, Start, Step, and Play."""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from backend.app.api.auth import require_permission
from backend.app.security.rbac import Permission, UserToken
from backend.app.api.state_manager import state_manager
from backend.app.orchestration.state import StateSnapshot

router = APIRouter(prefix="/scenario", tags=["Scenario Control"])


@router.post("/reset", response_model=StateSnapshot)
def reset_scenario(user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN))):
    """Reset the operational crisis environment to clean baseline scenario."""
    return state_manager.reset_scenario()


@router.post("/start", response_model=StateSnapshot)
def start_scenario(user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN))):
    """Ingest T0 disaster incidents and trigger multi-agent pipeline."""
    return state_manager.start_scenario()


@router.post("/step", response_model=StateSnapshot)
def step_scenario(user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN))):
    """Advance scenario to T+10 change events (submerged car, ambulance breakdown)."""
    return state_manager.step_scenario()


@router.post("/play")
def play_scenario(
    background_tasks: BackgroundTasks,
    speed: float = Query(1.0, ge=0.1, le=10.0, description="Playback speed multiplier"),
    user: UserToken = Depends(require_permission(Permission.TRIGGER_REPLAN)),
):
    """Play through complete disaster response demonstration automatically."""
    background_tasks.add_task(state_manager.play_scenario, speed=speed)
    return {
        "status": "PLAYING",
        "speed": speed,
        "message": "Scenario execution started in background with automated progression.",
    }
