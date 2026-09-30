"""Permission Manifest & Runtime Security Exceptions."""
from typing import Set
from pydantic import BaseModel, Field


class PermissionViolation(Exception):
    """Raised when an agent attempts an unauthorized tool execution or message dispatch."""
    def __init__(self, agent_name: str, action_type: str, item_name: str, message: str = ""):
        self.agent_name = agent_name
        self.action_type = action_type  # "tool" or "message_type"
        self.item_name = item_name
        self.message = message or f"Agent '{agent_name}' unauthorized to {action_type} '{item_name}'"
        super().__init__(self.message)


class PermissionManifest(BaseModel):
    """Strict security manifest defining an agent's runtime capabilities."""
    allowed_tools: Set[str] = Field(default_factory=set)
    allowed_inbound: Set[str] = Field(default_factory=set)
    allowed_outbound: Set[str] = Field(default_factory=set)
