"""
Dual-Indexed Timeline Journal.
Appends events to indexed SQLite store and mirrors to audit timeline.jsonl file.
Supports instant B-Tree catch-up replay queries for reconnecting desktop clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..config.constants import DEFAULT_JOURNAL_JSONL_NAME, EventType
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class TimelineJournal:
    """Coordinates session event logging across SQLite WAL and JSONL audit stream."""

    def __init__(
        self,
        session_id: str,
        sqlite_store: SQLiteStore,
        audit_file_dir: Optional[Path] = None,
    ) -> None:
        self.session_id = session_id
        self.sqlite = sqlite_store
        self.audit_dir = audit_file_dir or Path.cwd()
        self.audit_file = self.audit_dir / DEFAULT_JOURNAL_JSONL_NAME
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def record_event(self, event_type: EventType | str, payload: Dict[str, Any]) -> int:
        """
        Record a timeline event atomically.
        Returns the assigned sequence number.
        """
        etype = event_type.value if isinstance(event_type, EventType) else str(event_type)

        # 1. Record in SQLite B-tree store
        seq, event_id = self.sqlite.record_event(self.session_id, etype, payload)

        event_envelope = {
            "session_id": self.session_id,
            "seq": seq,
            "event_type": etype,
            "payload": payload,
            "timestamp": time.time(),
        }

        # 2. Append to JSONL audit log
        try:
            with self._lock:
                self.audit_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.audit_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event_envelope) + "\n")
        except Exception as e:
            logger.warning("Failed to append to JSONL audit file: %s", e)

        # 3. Notify real-time listeners (WebSocket hub)
        for listener in self._listeners:
            try:
                listener(event_envelope)
            except Exception as e:
                logger.error("Error in timeline listener: %s", e)

        return seq

    def get_events_after(self, last_seq: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Instant B-Tree lookup for client catch-up reconnection.
        """
        return self.sqlite.get_timeline_events(
            self.session_id, after_seq=last_seq, limit=limit
        )
