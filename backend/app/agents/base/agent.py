"""Base Agent with Runtime Permission Manifest Enforcement."""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
from backend.app.models.message import Message
from backend.app.security.manifest import PermissionManifest, PermissionViolation
from backend.app.agents.base.bus import MessageBus

logger = logging.getLogger("CrisisMesh.Agent")


class BaseAgent(ABC):
    """Abstract base agent enforcing tool and message type permissions at runtime."""

    def __init__(
        self,
        name: str,
        role: str,
        manifest: PermissionManifest,
        bus: MessageBus,
        tools: Optional[Dict[str, Callable]] = None,
    ):
        self.name = name
        self.role = role
        self.manifest = manifest
        self.bus = bus
        self.tools: Dict[str, Callable] = tools or {}

    def call_tool(self, name: str, trace_id: str = "sys-trace", **kwargs) -> Any:
        """Execute a tool while strictly enforcing manifest permissions.
        
        If the tool is not explicitly declared in `manifest.allowed_tools`,
        a security event is immediately published to the bus and a `PermissionViolation` is raised.
        """
        if name not in self.manifest.allowed_tools:
            logger.error(f"SECURITY VIOLATION: Agent '{self.name}' attempted unauthorized tool '{name}'")
            # Publish security violation event to the bus so it appears in the trace
            alert_msg = Message(
                sender=self.name,
                receiver="Guardian",
                type="SecurityViolation",
                payload={
                    "agent": self.name,
                    "violation_type": "disallowed_tool_call",
                    "target_tool": name,
                    "allowed_tools": list(self.manifest.allowed_tools),
                },
                trace_id=trace_id
            )
            self.bus.publish(alert_msg)
            raise PermissionViolation(self.name, "tool", name)

        if name not in self.tools:
            raise KeyError(f"Tool '{name}' authorized in manifest but not registered in agent runtime")

        return self.tools[name](**kwargs)

    def send_message(
        self,
        receiver: str,
        message_type: str,
        payload: Dict[str, Any],
        trace_id: str = "sys-trace",
    ) -> Message:
        """Send a typed message across the bus enforcing outbound permissions."""
        if message_type not in self.manifest.allowed_outbound:
            logger.error(f"SECURITY VIOLATION: Agent '{self.name}' attempted unauthorized outbound '{message_type}'")
            alert_msg = Message(
                sender=self.name,
                receiver="Guardian",
                type="SecurityViolation",
                payload={
                    "agent": self.name,
                    "violation_type": "disallowed_outbound_message",
                    "message_type": message_type,
                    "allowed_outbound": list(self.manifest.allowed_outbound),
                },
                trace_id=trace_id
            )
            self.bus.publish(alert_msg)
            raise PermissionViolation(self.name, "outbound_message", message_type)

        msg = Message(
            sender=self.name,
            receiver=receiver,
            type=message_type,
            payload=payload,
            trace_id=trace_id
        )
        self.bus.publish(msg)
        return msg

    def receive_message(self, message: Message) -> None:
        """Validate an incoming message against inbound manifest permissions."""
        if message.type not in self.manifest.allowed_inbound:
            logger.error(f"SECURITY VIOLATION: Agent '{self.name}' received disallowed inbound '{message.type}'")
            alert_msg = Message(
                sender="SecurityGate",
                receiver="Guardian",
                type="SecurityViolation",
                payload={
                    "agent": self.name,
                    "violation_type": "disallowed_inbound_message",
                    "message_type": message.type,
                    "allowed_inbound": list(self.manifest.allowed_inbound),
                },
                trace_id=message.trace_id
            )
            self.bus.publish(alert_msg)
            raise PermissionViolation(self.name, "inbound_message", message.type)

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent reasoning and produce state updates."""
        pass
