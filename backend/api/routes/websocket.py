from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.logger import get_logger
from typing import Dict, Set

log = get_logger(__name__)
router = APIRouter(tags=['websocket'])

# userId -> set of active WebSockets
_CONNECTIONS: Dict[str, Set[WebSocket]] = {}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    if user_id not in _CONNECTIONS:
        _CONNECTIONS[user_id] = set()
    _CONNECTIONS[user_id].add(websocket)
    log.info(f"WebSocket connected for user: {user_id}")
    
    try:
        while True:
            # Keep connection open and wait for messages (optional)
            data = await websocket.receive_json()
            # Handle incoming WS messages if needed
    except WebSocketDisconnect:
        _CONNECTIONS[user_id].remove(websocket)
        log.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        log.error(f"WebSocket error for user {user_id}: {e}")
        if user_id in _CONNECTIONS and websocket in _CONNECTIONS[user_id]:
            _CONNECTIONS[user_id].remove(websocket)

async def broadcast_user_update(user_id: str, payload: dict):
    """Utility to send updates to all active sessions of a user."""
    if user_id in _CONNECTIONS:
        for ws in list(_CONNECTIONS[user_id]):
            try:
                await ws.send_json(payload)
            except Exception:
                _CONNECTIONS[user_id].remove(ws)
