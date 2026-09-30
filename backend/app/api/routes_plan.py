"""Plan & State API Routes: State Snapshot, Current Plan, Plan Diffs, Approval & Rejection."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.schemas import PlanApproveRequest, PlanRejectRequest
from backend.app.api.auth import require_permission, get_current_user
from backend.app.security.rbac import Permission, UserToken, CommanderToken
from backend.app.api.state_manager import state_manager
from backend.app.models.schemas import Plan, PlanDiff
from backend.app.orchestration.state import StateSnapshot

router = APIRouter(tags=["State & Plans"])


@router.get("/state", response_model=StateSnapshot)
def get_disaster_state(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Retrieve full operational snapshot of current disaster response state."""
    return state_manager.get_snapshot()


@router.get("/plan/current", response_model=Plan)
def get_current_plan(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Retrieve current proposed or active resource allocation plan."""
    curr_plan = state_manager.state.get("current_plan")
    if not curr_plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active or proposed plan formulated yet.")
    return curr_plan


@router.get("/plan/diff", response_model=PlanDiff)
def get_plan_diff(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Retrieve delta between previously approved plan and current revision."""
    diff = state_manager.state.get("plan_diff")
    if not diff:
        return PlanDiff(new_plan_id="none", summary="No plan revisions generated yet", changes=[])
    return diff


@router.post("/plan/{plan_id}/approve")
def approve_plan(
    plan_id: str,
    req: PlanApproveRequest,
    user: UserToken = Depends(require_permission(Permission.APPROVE_PLAN)),
):
    """Authorize resource plan. Strictly enforces Commander role and Ed25519 cryptographic signature."""
    if not isinstance(user, CommanderToken):
        from backend.app.models.schemas import SecurityEvent
        from backend.app.api.websocket import ws_manager
        msg = f"Privilege escalation blocked: Role '{user.role.value}' is not authorized to sign dispatch authorizations."
        sec_event = SecurityEvent(
            event_type="privilege_escalation_attempt",
            severity="CRITICAL",
            agent_name="ApprovalGate",
            description=msg,
        )
        state_manager.security_events.append(sec_event)
        state_manager.bus.log_security_event(sec_event.event_type, "ApprovalGate", sec_event.model_dump())
        ws_manager.emit(event_type="security_event", payload=sec_event.model_dump(mode="json"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=msg,
        )

    result = state_manager.approve_plan(
        plan_id=plan_id,
        signature_hex=req.signature_hex,
        nonce=req.nonce,
        timestamp=req.timestamp,
        commander_token=user,
        decisions=req.decisions,
        auto_sign=req.auto_sign,
    )

    if result.get("status") == "DISPATCH_BLOCKED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cryptographic dispatch verification failed: {result.get('error')}",
        )

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    return result


@router.post("/plan/{plan_id}/reject")
def reject_plan(
    plan_id: str,
    req: PlanRejectRequest,
    user: UserToken = Depends(require_permission(Permission.REJECT_PLAN)),
):
    """Commander rejects proposed plan with mandatory operational rationale, triggering re-plan."""
    if not isinstance(user, CommanderToken):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only certified commanders can reject allocation proposals.",
        )

    result = state_manager.reject_plan(
        plan_id=plan_id,
        reason=req.reason,
        forbidden_pairs=req.forbidden_pairs,
    )
    return result
