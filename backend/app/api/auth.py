"""Authentication Service: Abstract Interface, Dev JWT Implementation, and FastAPI Dependencies."""
from __future__ import annotations
from abc import ABC, abstractmethod
import os
import time
from typing import Optional, Dict, Tuple, Any, Callable
import jwt
from fastapi import Depends, HTTPException, Security, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.security.rbac import Role, Permission, UserToken, CommanderToken, RBACManager, RBACError
from backend.app.security.crypto import CommanderKeyManager

JWT_SECRET = os.getenv("CRISISMESH_JWT_SECRET", "crisismesh-dev-jwt-secret-key-32bytes-long!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 7200  # 2 hours


def is_demo_mode() -> bool:
    """Return True only if CRISISMESH_DEMO_MODE is explicitly enabled. Defaults to FALSE."""
    return os.getenv("CRISISMESH_DEMO_MODE", "false").lower() in ("true", "1", "yes")


bearer_scheme = HTTPBearer(auto_error=False)


class AuthService(ABC):
    """Abstract authentication service interface (swappable with Supabase Auth or Clerk)."""

    @abstractmethod
    def authenticate(self, username: str, password: str, role_hint: Optional[Role] = None) -> Optional[UserToken]:
        pass

    @abstractmethod
    def create_token(self, token_model: UserToken) -> str:
        pass

    @abstractmethod
    def verify_token(self, token_str: str) -> UserToken:
        pass


class DevJWTAuthService(AuthService):
    """Deterministic development JWT authenticator supporting viewer, operator, and commander.

    CRITICAL SECURITY INVARIANT:
    Demo accounts exist ONLY when CRISISMESH_DEMO_MODE=true.
    When demo mode is unset or false, dev_users is empty and authentication fails.
    """

    @property
    def dev_users(self) -> Dict[str, Tuple[str, Role]]:
        if not is_demo_mode():
            return {}
        return {
            "viewer": ("viewer123", Role.VIEWER),
            "operator": ("operator123", Role.OPERATOR),
            "commander": ("commander123", Role.COMMANDER),
        }

    # Backward compatibility class-level attribute mapping to the dynamic property
    DEV_USERS = property(lambda self: self.dev_users)

    def __init__(self, key_manager: Optional[CommanderKeyManager] = None):
        self.key_manager = key_manager or CommanderKeyManager()

    def authenticate(self, username: str, password: str, role_hint: Optional[Role] = None) -> Optional[UserToken]:
        user_info = self.dev_users.get(username.lower())
        if not user_info:
            return None
        expected_pass, role = user_info
        if password != expected_pass:
            return None

        # Allow role override if valid dev request
        final_role = role_hint if role_hint else role

        if final_role == Role.COMMANDER:
            return CommanderToken(
                user_id=username,
                role=Role.COMMANDER,
                public_key_hex=self.key_manager.get_public_key_hex(),
                badge_number="CMD-BLR-001",
                issued_at=time.time(),
                expires_at=time.time() + JWT_EXPIRATION_SECONDS,
            )
        else:
            return UserToken(
                user_id=username,
                role=final_role,
                issued_at=time.time(),
                expires_at=time.time() + JWT_EXPIRATION_SECONDS,
            )

    def create_token(self, token_model: UserToken) -> str:
        payload = {
            "sub": token_model.user_id,
            "role": token_model.role.value,
            "iat": int(token_model.issued_at),
            "exp": int(token_model.expires_at or (time.time() + JWT_EXPIRATION_SECONDS)),
        }
        if isinstance(token_model, CommanderToken):
            payload["public_key_hex"] = token_model.public_key_hex
            if token_model.badge_number:
                payload["badge_number"] = token_model.badge_number

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token_str: str) -> UserToken:
        try:
            payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            role_str = payload.get("role")
            if not user_id or not role_str:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

            role = Role(role_str)
            if role == Role.COMMANDER:
                return CommanderToken(
                    user_id=user_id,
                    role=Role.COMMANDER,
                    public_key_hex=payload.get("public_key_hex", self.key_manager.get_public_key_hex()),
                    badge_number=payload.get("badge_number"),
                    issued_at=float(payload.get("iat", time.time())),
                    expires_at=float(payload.get("exp", time.time() + JWT_EXPIRATION_SECONDS)),
                )
            else:
                return UserToken(
                    user_id=user_id,
                    role=role,
                    issued_at=float(payload.get("iat", time.time())),
                    expires_at=float(payload.get("exp", time.time() + JWT_EXPIRATION_SECONDS)),
                )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except (jwt.InvalidTokenError, ValueError) as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {e}")


# Singleton instance
auth_service = DevJWTAuthService()


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
) -> UserToken:
    """Resolve current user from Authorization header or WebSocket query param."""
    token_str = None
    if auth_header and auth_header.credentials:
        token_str = auth_header.credentials
    elif token_query:
        token_str = token_query

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials (provide Bearer token or ?token= param)",
        )

    return auth_service.verify_token(token_str)


def require_permission(perm: Permission) -> Callable[[UserToken], UserToken]:
    """Dependency factory checking user permission."""
    def _dependency(user: UserToken = Depends(get_current_user)) -> UserToken:
        has_perm, msg = RBACManager.check_access(user, perm)
        if not has_perm:
            from backend.app.models.schemas import SecurityEvent
            from backend.app.api.state_manager import state_manager
            from backend.app.api.websocket import ws_manager
            sec_event = SecurityEvent(
                event_type="rbac_permission_denied",
                severity="HIGH",
                agent_name="RBACManager",
                description=f"User '{user.user_id}' ({user.role.value}) denied '{perm.value}': {msg}",
            )
            state_manager.security_events.append(sec_event)
            state_manager.bus.log_security_event(sec_event.event_type, "RBACManager", sec_event.model_dump())
            ws_manager.emit(event_type="security_event", payload=sec_event.model_dump(mode="json"))
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        return user
    return _dependency


def require_role(*roles: Role) -> Callable[[UserToken], UserToken]:
    """Dependency factory checking specific role membership."""
    def _dependency(user: UserToken = Depends(get_current_user)) -> UserToken:
        if user.role not in roles:
            from backend.app.models.schemas import SecurityEvent
            from backend.app.api.state_manager import state_manager
            from backend.app.api.websocket import ws_manager
            role_names = [r.value for r in roles]
            msg = f"Access denied: Role '{user.role.value}' not in authorized roles {role_names}"
            sec_event = SecurityEvent(
                event_type="rbac_role_denied",
                severity="HIGH",
                agent_name="RBACManager",
                description=f"User '{user.user_id}' ({user.role.value}) denied role requirement {role_names}",
            )
            state_manager.security_events.append(sec_event)
            state_manager.bus.log_security_event(sec_event.event_type, "RBACManager", sec_event.model_dump())
            ws_manager.emit(event_type="security_event", payload=sec_event.model_dump(mode="json"))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=msg,
            )
        return user
    return _dependency
