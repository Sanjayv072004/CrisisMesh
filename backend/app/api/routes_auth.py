"""Authentication API Routes."""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException, Depends, Query, status
from backend.app.api.schemas import LoginRequest, TokenResponse
from backend.app.api.auth import auth_service, get_current_user, is_demo_mode
from backend.app.security.rbac import Role, UserToken, CommanderToken

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate and obtain a development JWT token with embedded RBAC role."""
    token_model = auth_service.authenticate(req.username, req.password, role_hint=req.role)
    if not token_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Note: Dev demo accounts require CRISISMESH_DEMO_MODE=true.",
        )

    jwt_token = auth_service.create_token(token_model)
    pub_key = getattr(token_model, "public_key_hex", None)

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        role=token_model.role.value,
        user_id=token_model.user_id,
        public_key_hex=pub_key,
    )


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(
    role: Role = Query(Role.VIEWER, description="Role to assume: viewer, operator, commander")
):
    """One-click demo login without credentials. Enabled ONLY when CRISISMESH_DEMO_MODE=true."""
    if not is_demo_mode():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is disabled. Set CRISISMESH_DEMO_MODE=true in your environment to enable demonstration mode.",
        )

    user_id = f"demo_{role.value}"
    if role == Role.COMMANDER:
        token_model = CommanderToken(
            user_id=user_id,
            role=Role.COMMANDER,
            public_key_hex=auth_service.key_manager.get_public_key_hex(),
            badge_number="CMD-DEMO-001",
            issued_at=time.time(),
            expires_at=time.time() + 3600,  # Short-lived 1 hour
        )
    else:
        token_model = UserToken(
            user_id=user_id,
            role=role,
            issued_at=time.time(),
            expires_at=time.time() + 3600,  # Short-lived 1 hour
        )

    jwt_token = auth_service.create_token(token_model)
    pub_key = getattr(token_model, "public_key_hex", None)

    # Audit log the demo login event
    from backend.app.models.schemas import SecurityEvent
    from backend.app.api.state_manager import state_manager
    from backend.app.api.websocket import ws_manager
    sec_event = SecurityEvent(
        event_type="demo_login_authenticated",
        severity="LOW",
        agent_name="AuthService",
        description=f"Demo session token issued for role '{role.value}' (user: {user_id})",
        metadata={"role": role.value, "user_id": user_id, "expires_in_seconds": 3600}
    )
    state_manager.security_events.append(sec_event)
    state_manager.bus.log_security_event(sec_event.event_type, "AuthService", sec_event.model_dump())
    ws_manager.emit(event_type="security_event", payload=sec_event.model_dump(mode="json"))

    return TokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        role=token_model.role.value,
        user_id=token_model.user_id,
        public_key_hex=pub_key,
        expires_in_seconds=3600,
    )


@router.get("/me")
def get_current_user_profile(user: UserToken = Depends(get_current_user)):
    """Retrieve identity and authorized role of the authenticated token bearer."""
    return {
        "user_id": user.user_id,
        "role": user.role.value,
        "public_key_hex": getattr(user, "public_key_hex", None),
        "issued_at": user.issued_at,
        "expires_at": user.expires_at,
    }
