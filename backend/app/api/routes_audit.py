"""Audit & Security API Routes: Tamper-Evident Hash Chain & Security Events."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from backend.app.api.auth import require_permission
from backend.app.security.rbac import Permission, UserToken
from backend.app.api.state_manager import state_manager

router = APIRouter(tags=["Audit & Security"])


@router.get("/audit")
def get_audit_trail(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Retrieve full append-only tamper-evident audit chain."""
    entries = state_manager.bus.audit_chain.get_entries()
    return {
        "count": len(entries),
        "entries": [e.model_dump() for e in entries],
    }


@router.get("/audit/verify")
def verify_audit_integrity(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Perform mathematical verification of SHA-256 hash chaining from Genesis to head."""
    is_valid, broken_idx = state_manager.bus.audit_chain.verify_chain()
    return {
        "is_valid": is_valid,
        "broken_index": broken_idx,
        "total_entries": len(state_manager.bus.audit_chain),
        "status": "CHAIN_INTEGRITY_VERIFIED" if is_valid else f"INTEGRITY_COMPROMISED_AT_BLOCK_{broken_idx}",
    }


@router.get("/security/events")
def get_security_events(user: UserToken = Depends(require_permission(Permission.VIEW))):
    """Retrieve all security violations, injection attempts, and perimeter alerts."""
    return {
        "count": len(state_manager.security_events),
        "events": [e.model_dump() for e in state_manager.security_events],
    }
