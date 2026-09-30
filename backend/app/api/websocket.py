"""WebSocket Connection Manager: Real-Time Event Streaming & Monotonic Replay."""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from backend.app.api.schemas import WSEvent


class ConnectionManager:
    """Manages connected frontend WebSocket clients and provides historical replay."""

    def __init__(self, max_history: int = 2000):
        self.active_connections: List[WebSocket] = []
        self.event_history: List[WSEvent] = []
        self.max_history = max_history
        self._seq_counter = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _next_event_id(self) -> str:
        self._seq_counter += 1
        return f"evt_{self._seq_counter:06d}_{uuid.uuid4().hex[:6]}"

    async def connect(self, websocket: WebSocket, last_event_id: Optional[str] = None) -> None:
        """Accept new WebSocket connection and replay missed events if last_event_id is provided."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self._loop = asyncio.get_running_loop()

        # Replay missed events from buffer upon reconnect
        if last_event_id:
            await self._replay_since(websocket, last_event_id)

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _replay_since(self, websocket: WebSocket, last_event_id: str) -> None:
        """Replay all buffered events occurring strictly after last_event_id."""
        replay_events: List[WSEvent] = []
        found = False
        for evt in self.event_history:
            if found:
                replay_events.append(evt)
            elif evt.id == last_event_id:
                found = True

        for event in replay_events:
            try:
                await websocket.send_text(event.model_dump_json())
            except Exception:
                break

    async def _send_to_active(self, event: WSEvent) -> None:
        """Send event JSON string to all currently active connections."""
        event_json = event.model_dump_json()
        disconnected: List[WebSocket] = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(event_json)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast(self, event: WSEvent) -> None:
        """Append to buffer and send to active connections."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        await self._send_to_active(event)

    def emit(self, event_type: str, payload: Dict[str, Any], trace_id: Optional[str] = None) -> WSEvent:
        """Thread-safe synchronous event emission to all connected WebSocket clients."""
        evt_id = self._next_event_id()
        event = WSEvent(
            id=evt_id,
            type=event_type,
            timestamp=time.time(),
            trace_id=trace_id or f"trace-{uuid.uuid4().hex[:8]}",
            payload=payload,
        )

        # Store in historical replay buffer immediately
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Safely dispatch to active client websockets
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send_to_active(event), self._loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._send_to_active(event))
            except RuntimeError:
                pass

        return event

    def clear(self) -> None:
        """Clear event buffer and sequence counter."""
        self.event_history.clear()
        self._seq_counter = 0


# Singleton instance
ws_manager = ConnectionManager()
