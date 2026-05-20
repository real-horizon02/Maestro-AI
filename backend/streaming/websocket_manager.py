"""
WebSocket Connection Manager — handles real-time streaming to frontend clients.
Maintains a registry of active WebSocket connections per task_id.
"""

import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for streaming task progress.
    Multiple clients can subscribe to the same task_id.
    """

    def __init__(self):
        # task_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection for a task."""
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(websocket)
        logger.info(f"[WS] Client connected for task {task_id}. Total: {len(self._connections[task_id])}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        """Remove a disconnected WebSocket from the registry."""
        if task_id in self._connections:
            try:
                self._connections[task_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[task_id]:
                del self._connections[task_id]
        logger.info(f"[WS] Client disconnected from task {task_id}")

    async def broadcast(self, task_id: str, message: dict):
        """
        Send a JSON message to all clients subscribed to task_id.
        Silently removes dead connections.
        """
        if task_id not in self._connections:
            return

        dead = []
        for ws in self._connections[task_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(task_id, ws)

    async def send_event(self, task_id: str, event_type: str, agent: str, content: str, extra: dict = None):
        """
        Structured event broadcaster.
        event_type: started | progress | completed | failed | final
        """
        payload = {
            "event": event_type,
            "agent": agent,
            "content": content,
            "task_id": task_id,
        }
        if extra:
            payload.update(extra)
        await self.broadcast(task_id, payload)

    def active_tasks(self) -> List[str]:
        """Return list of task_ids with active connections."""
        return list(self._connections.keys())

    def connection_count(self, task_id: str) -> int:
        return len(self._connections.get(task_id, []))


# Singleton manager — shared across the FastAPI app
manager = ConnectionManager()
