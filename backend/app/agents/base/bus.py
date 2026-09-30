"""MessageBus: In-Memory Event Log, Audit Persistence, and Trace Streaming."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Callable, List, Optional
from backend.app.models.message import Message
from backend.app.audit.chain import AuditChain, AuditEntry


class MessageBus:
    """Thread-safe event bus for inter-agent communication and cryptographic audit tracing."""

    def __init__(
        self,
        audit_store_path: Optional[Path] = None,
        audit_chain: Optional[AuditChain] = None,
    ):
        self._in_memory_log: List[Message] = []
        self._subscribers: List[Callable[[Message], None]] = []
        self.audit_store_path = audit_store_path

        if self.audit_store_path:
            self.audit_store_path.parent.mkdir(parents=True, exist_ok=True)

        # Tamper-evident SHA-256 cryptographic audit chain
        self.audit_chain = audit_chain or AuditChain(log_path=audit_store_path)

    def subscribe(self, callback: Callable[[Message], None]) -> None:
        """Register a subscriber (e.g. for WebSocket trace streaming)."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Message], None]) -> None:
        """Remove a registered subscriber."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def publish(self, message: Message) -> None:
        """Publish a typed message to the bus.
        
        1. Appends to the in-memory event log.
        2. Appends to the tamper-evident hash-chained audit log.
        3. Dispatches to all active subscribers.
        """
        # 1. In-memory log
        self._in_memory_log.append(message)

        # 2. Append to tamper-evident audit chain
        try:
            self.audit_chain.append(
                event_type=message.type,
                actor=message.sender,
                payload=message.payload,
            )
        except Exception as e:
            print(f"[MessageBus] Audit chain append error: {e}")

        # 3. Stream to subscribers
        for subscriber in list(self._subscribers):
            try:
                subscriber(message)
            except Exception as e:
                print(f"[MessageBus] Subscriber error: {e}")

    def log_security_event(self, event_type: str, actor: str, payload: dict) -> AuditEntry:
        """Log a security event directly into the tamper-evident audit chain."""
        return self.audit_chain.append(
            event_type=f"SECURITY:{event_type}",
            actor=actor,
            payload=payload,
        )

    def verify_audit_log(self):
        """Verify the integrity of the audit chain."""
        return self.audit_chain.verify_chain()

    def get_trace(self, trace_id: Optional[str] = None) -> List[Message]:
        """Retrieve the sequence of messages, optionally filtered by trace_id."""
        if trace_id is None:
            return list(self._in_memory_log)
        return [msg for msg in self._in_memory_log if msg.trace_id == trace_id]

    def clear(self) -> None:
        """Clear the in-memory log."""
        self._in_memory_log.clear()
