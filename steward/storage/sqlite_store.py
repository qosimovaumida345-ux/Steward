"""
Local SQLite Store with WAL Mode and B-Tree Indexed Timeline Reconnect.
Provides sub-millisecond local persistence and offline transaction outbox.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config.constants import DEFAULT_DATA_DIR, SQLITE_BUSY_TIMEOUT_MS
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class SQLiteStore:
    """Thread-safe, WAL-enabled SQLite persistence manager."""

    SCHEMA_DDL = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        current_model TEXT,
        context_tokens INTEGER DEFAULT 0,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        metadata TEXT DEFAULT '{}'
    );

    CREATE TABLE IF NOT EXISTS timeline_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at REAL NOT NULL,
        synced_to_cloud INTEGER DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_timeline_session_seq 
    ON timeline_events(session_id, seq);

    CREATE TABLE IF NOT EXISTS sync_outbox (
        outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at REAL NOT NULL,
        attempt_count INTEGER DEFAULT 0,
        last_error TEXT,
        status TEXT DEFAULT 'pending'
    );

    CREATE INDEX IF NOT EXISTS idx_outbox_status 
    ON sync_outbox(status, outbox_id);

    CREATE TABLE IF NOT EXISTS file_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        content TEXT NOT NULL,
        hash TEXT NOT NULL,
        mtime REAL NOT NULL,
        created_at REAL NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_snapshots_path 
    ON file_snapshots(file_path, created_at DESC);
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            settings = get_settings()
            self.db_path = settings.sqlite_path
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                timeout=SQLITE_BUSY_TIMEOUT_MS / 1000.0,
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row
            # Configure high-performance WAL and memory options
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS};")
            cursor.execute("PRAGMA mmap_size = 268435456;")  # 256 MB mmap
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.close()
        return self._conn

    def _init_database(self) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.executescript(self.SCHEMA_DDL)
            conn.commit()

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    # ---------------- Session Management ----------------

    def create_session(
        self,
        session_id: str,
        title: str,
        status: str = "IDLE",
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = time.time()
        meta_json = json.dumps(metadata or {})
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT INTO sessions (session_id, title, status, current_model, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    title=excluded.title,
                    updated_at=excluded.updated_at,
                    metadata=excluded.metadata;
                """,
                (session_id, title, status, model, now, now, meta_json),
            )
            conn.commit()
        return self.get_session(session_id) or {}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?;", (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["metadata"] = json.loads(res.get("metadata", "{}"))
            except Exception:
                pass
            return res

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?;", (limit,)
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                try:
                    item["metadata"] = json.loads(item.get("metadata", "{}"))
                except Exception:
                    pass
                result.append(item)
            return result

    def update_session_status(
        self, session_id: str, status: str, context_tokens: Optional[int] = None
    ) -> None:
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            if context_tokens is not None:
                conn.execute(
                    """
                    UPDATE sessions 
                    SET status = ?, context_tokens = ?, updated_at = ?
                    WHERE session_id = ?;
                    """,
                    (status, context_tokens, now, session_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE sessions 
                    SET status = ?, updated_at = ?
                    WHERE session_id = ?;
                    """,
                    (status, now, session_id),
                )
            conn.commit()

    # ---------------- Event Recording & Outbox ----------------

    def record_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Tuple[int, int]:
        """
        Atomically records a timeline event with auto-incrementing sequence number
        and writes it into the sync_outbox for cloud replication.
        Returns (seq, event_id).
        """
        now = time.time()
        payload_str = json.dumps(payload)

        with self._lock:
            conn = self._get_connection()
            # Calculate next sequence number for this session
            cursor = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM timeline_events WHERE session_id = ?;",
                (session_id,),
            )
            next_seq = cursor.fetchone()[0]

            # Insert into timeline_events
            cursor = conn.execute(
                """
                INSERT INTO timeline_events (session_id, seq, event_type, payload, created_at, synced_to_cloud)
                VALUES (?, ?, ?, ?, ?, 0);
                """,
                (session_id, next_seq, event_type, payload_str, now),
            )
            event_id = cursor.lastrowid

            # Insert into sync_outbox
            conn.execute(
                """
                INSERT INTO sync_outbox (session_id, seq, event_type, payload, created_at, status)
                VALUES (?, ?, ?, ?, ?, 'pending');
                """,
                (session_id, next_seq, event_type, payload_str, now),
            )

            # Update session's updated_at
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?;",
                (now, session_id),
            )

            conn.commit()
            return next_seq, event_id

    def get_timeline_events(
        self, session_id: str, after_seq: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Indexed B-Tree lookup for instant catch-up synchronization.
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT seq, event_type, payload, created_at 
                FROM timeline_events 
                WHERE session_id = ? AND seq > ? 
                ORDER BY seq ASC 
                LIMIT ?;
                """,
                (session_id, after_seq, limit),
            )
            rows = cursor.fetchall()
            events = []
            for r in rows:
                item = dict(r)
                try:
                    item["payload"] = json.loads(item["payload"])
                except Exception:
                    pass
                events.append(item)
            return events

    # ---------------- Outbox Synchronization API ----------------

    def fetch_pending_outbox_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT * FROM sync_outbox 
                WHERE status = 'pending' 
                ORDER BY outbox_id ASC 
                LIMIT ?;
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def mark_outbox_items_synced(self, outbox_ids: List[int]) -> None:
        if not outbox_ids:
            return
        placeholders = ",".join("?" for _ in outbox_ids)
        with self._lock:
            conn = self._get_connection()
            # Update outbox status to synced
            conn.execute(
                f"UPDATE sync_outbox SET status = 'synced' WHERE outbox_id IN ({placeholders});",
                outbox_ids,
            )
            conn.commit()

    def record_outbox_failure(self, outbox_id: int, error: str, max_attempts: int = 10) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT attempt_count FROM sync_outbox WHERE outbox_id = ?;", (outbox_id,)
            )
            row = cursor.fetchone()
            if not row:
                return
            new_attempts = row[0] + 1
            new_status = "dead_letter" if new_attempts >= max_attempts else "pending"
            conn.execute(
                """
                UPDATE sync_outbox 
                SET attempt_count = ?, last_error = ?, status = ?
                WHERE outbox_id = ?;
                """,
                (new_attempts, error, new_status, outbox_id),
            )
            conn.commit()

    # ---------------- Snapshot Rollback Storage ----------------

    def save_file_snapshot(
        self, file_path: str, content: str, content_hash: str, mtime: float
    ) -> None:
        now = time.time()
        with self._lock:
            conn = self._get_connection()
            conn.execute(
                """
                INSERT INTO file_snapshots (file_path, content, hash, mtime, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (file_path, content, content_hash, mtime, now),
            )
            conn.commit()

    def get_latest_snapshot(self, file_path: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                """
                SELECT * FROM file_snapshots 
                WHERE file_path = ? 
                ORDER BY created_at DESC 
                LIMIT 1;
                """,
                (file_path,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
