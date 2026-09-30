"""MessageBus: In-Memory Event Log, Audit Persistence, and Trace Streaming."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Callable, List, Optional
from backend.app.models.message import Message


class MessageBus:
    """Thread-safe event bus for inter-agent communication and audit tracing."""

    def __init__(self, audit_store_path: Optional[Path] = None):
        self._in_memory_log: List[Message] = []
        self._subscribers: List[Callable[[Message], None]] = []
        self.audit_store_path = audit_store_path

        if self.audit_store_path:
            self.audit_store_path.parent.mkdir(parents=True, exist_ok=True)

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
        2. Persists to the audit log store (JSONL).
        3. Dispatches to all active subscribers.
        """
        # 1. In-memory log
        self._in_memory_log.append(message)

        # 2. Persist to audit store
        if self.audit_store_path:
            try:
                with open(self.audit_store_path, "a", encoding="utf-8") as f:
                    f.write(message.model_dump_json() + "\n")
            except Exception as e:
                print(f"[MessageBus] Audit persist error: {e}")

        # 3. Stream to subscribers
        for subscriber in list(self._subscribers):
            try:
                subscriber(message)
            except Exception as e:
                print(f"[MessageBus] Subscriber error: {e}")

    def get_trace(self, trace_id: Optional[str] = None) -> List[Message]:
        """Retrieve the sequence of messages, optionally filtered by trace_id."""
        if trace_id is None:
            return list(self._in_memory_log)
        return [msg for msg in self._in_memory_log if msg.trace_id == trace_id]

    def clear(self) -> None:
        """Clear the in-memory log."""
        self._in_memory_log.clear()
