"""Typed Message Schema for Inter-Agent Bus Communication."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Typed Message model exchanged across the CrisisMesh message bus."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    receiver: str
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
