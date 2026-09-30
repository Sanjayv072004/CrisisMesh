"""WebSocket API Route: Authenticated Real-Time Streaming and Historical Replay."""
from __future__ import annotations
import json
import time
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from backend.app.api.websocket import ws_manager
from backend.app.api.auth import auth_service

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Bearer JWT token for authentication"),
    last_event_id: Optional[str] = Query(None, description="Event ID for historical replay upon reconnection"),
):
    """Real-time event stream emitting typed operational events with reconnection replay."""
    # 1. JWT Authentication
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    try:
        user = auth_service.verify_token(token)
    except Exception as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Invalid token: {e}")
        return

    # 2. Connect client and perform replay if requested
    await ws_manager.connect(websocket, last_event_id=last_event_id)

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
