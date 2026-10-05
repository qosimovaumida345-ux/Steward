"""
WebSocket Hub: Attach/Detach Protocol and Catch-Up Replay.
Provides real-time streaming to desktop clients and instant indexed catch-up on reconnection.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Set

from aiohttp import web, WSMsgType

from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Manages active WebSocket connections, catch-up replays, and event broadcasting."""

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        self.sqlite = sqlite_store
        # session_id -> Set[web.WebSocketResponse]
        self._connections: Dict[str, Set[web.WebSocketResponse]] = {}
        self._lock = asyncio.Lock()

    async def register_connection(self, session_id: str, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            self._connections[session_id].add(ws)
        logger.info("Client connected to session %s (total: %d)", session_id, len(self._connections[session_id]))

    async def unregister_connection(self, session_id: str, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            if session_id in self._connections:
                self._connections[session_id].discard(ws)
                if not self._connections[session_id]:
                    del self._connections[session_id]
        logger.info("Client disconnected from session %s", session_id)

    async def replay_catch_up(
        self, ws: web.WebSocketResponse, session_id: str, last_seq: int = 0
    ) -> int:
        """
        Stream events with seq > last_seq from indexed SQLite store.
        Returns the number of events replayed.
        """
        events = self.sqlite.get_timeline_events(session_id, after_seq=last_seq, limit=500)
        for ev in events:
            msg = {
                "type": "timeline_event",
                "session_id": session_id,
                "seq": ev["seq"],
                "event_type": ev["event_type"],
                "payload": ev["payload"],
                "created_at": ev["created_at"],
            }
            await ws.send_json(msg)

        # Send catch-up completion marker
        highest_seq = events[-1]["seq"] if events else last_seq
        await ws.send_json({
            "type": "catch_up_complete",
            "session_id": session_id,
            "last_seq": highest_seq,
            "count": len(events),
        })
        return len(events)

    async def broadcast_event(self, session_id: str, event_data: Dict[str, Any]) -> None:
        """Broadcast live event to all attached clients of this session."""
        async with self._lock:
            sockets = list(self._connections.get(session_id, []))

        if not sockets:
            return

        msg = {
            "type": "timeline_event",
            "session_id": session_id,
            "seq": event_data.get("seq", 0),
            "event_type": event_data.get("event_type", "unknown"),
            "payload": event_data.get("payload", {}),
            "timestamp": event_data.get("timestamp"),
        }

        dead_sockets = []
        for ws in sockets:
            try:
                if not ws.closed:
                    await ws.send_json(msg)
                else:
                    dead_sockets.append(ws)
            except Exception as e:
                logger.debug("Failed sending to client: %s", e)
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead_ws in dead_sockets:
                    self._connections.get(session_id, set()).discard(dead_ws)
