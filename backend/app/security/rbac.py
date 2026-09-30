"""Role-Based Access Control (RBAC): Hierarchical Permissions & Token Validation."""
from __future__ import annotations
from enum import Enum
import time
from typing import Set, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field


class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    COMMANDER = "commander"


class Permission(str, Enum):
    VIEW = "view"
    SUBMIT_REPORT = "submit_report"
    TRIGGER_REPLAN = "trigger_replan"
    APPROVE_PLAN = "approve_plan"
    REJECT_PLAN = "reject_plan"
    OVERRIDE_CONSTRAINTS = "override_constraints"
    DISPATCH_FLEET = "dispatch_fleet"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.VIEW,
    },
    Role.OPERATOR: {
        Permission.VIEW,
        Permission.SUBMIT_REPORT,
        Permission.TRIGGER_REPLAN,
    },
    Role.COMMANDER: {
        Permission.VIEW,
        Permission.SUBMIT_REPORT,
        Permission.TRIGGER_REPLAN,
        Permission.APPROVE_PLAN,
        Permission.REJECT_PLAN,
        Permission.OVERRIDE_CONSTRAINTS,
        Permission.DISPATCH_FLEET,
    },
}


class UserToken(BaseModel):
    """User identity token carried in API headers or agent requests."""
    user_id: str
    role: Role
    issued_at: float = Field(default_factory=time.time)
    expires_at: Optional[float] = None

    model_config = {"extra": "forbid"}

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CommanderToken(UserToken):
    """Cryptographic authorization token exclusively issued to certified incident commanders."""
    role: Role = Role.COMMANDER
    public_key_hex: str
    badge_number: Optional[str] = None


class RBACError(Exception):
    """Raised when an operation violates Role-Based Access Control policies."""
    pass


class RBACManager:
    """RBAC validation and enforcement engine."""

    @staticmethod
    def has_permission(token: UserToken, required_perm: Permission) -> bool:
        """Check if a token has the requested permission."""
        if token.is_expired():
            return False
        allowed = ROLE_PERMISSIONS.get(token.role, set())
        return required_perm in allowed

    @classmethod
    def check_access(cls, token: UserToken, required_perm: Permission) -> Tuple[bool, str]:
        """Validate permission and return explanatory message."""
        if token.is_expired():
            return False, f"Token for user '{token.user_id}' has expired."
        if not cls.has_permission(token, required_perm):
            return False, (
                f"Access denied: User '{token.user_id}' with role '{token.role.value}' "
                f"does not hold required permission '{required_perm.value}'."
            )
        return True, "Access granted."

    @classmethod
    def enforce_commander_token(cls, token: Any) -> Tuple[bool, str]:
        """Strictly verify that the actor possesses a valid CommanderToken."""
        if not isinstance(token, UserToken):
            return False, "Missing or invalid authentication token: must be a UserToken instance."
        if token.is_expired():
            return False, f"Commander token for '{token.user_id}' has expired."
        if token.role != Role.COMMANDER:
            return False, (
                f"Privilege escalation blocked: Role '{token.role.value}' is not authorized "
                f"for commander-level operations (requires 'commander')."
            )
        if not isinstance(token, CommanderToken) or not token.public_key_hex:
            return False, "Commander operations require a valid CommanderToken with a bound Ed25519 public key."
        return True, "Commander token validated."
