"""Authentication API Routes."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.api.schemas import LoginRequest, TokenResponse
from backend.app.api.auth import auth_service, get_current_user
from backend.app.security.rbac import UserToken, CommanderToken

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate and obtain a development JWT token with embedded RBAC role."""
    token_model = auth_service.authenticate(req.username, req.password, role_hint=req.role)
    if not token_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password. Dev accounts: viewer/viewer123, operator/operator123, commander/commander123",
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
