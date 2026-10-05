"""
Cloud PostgreSQL Client for Render Multi-Device Sync.
Supports psycopg2 and pg8000 with threadpool async execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _format_pg8000_query(sql: str, params: tuple | list) -> tuple[str, dict]:
    parts = sql.split("%s")
    if len(parts) - 1 != len(params):
        raise ValueError(f"Param count mismatch: expected {len(parts) - 1}, got {len(params)}")
    new_sql = []
    kwargs = {}
    for i in range(len(params)):
        new_sql.append(parts[i])
        new_sql.append(f":p{i}")
        kwargs[f"p{i}"] = params[i]
    new_sql.append(parts[-1])
    return "".join(new_sql), kwargs


class RenderPostgresClient:
    """Async adapter for Render Cloud PostgreSQL synchronization."""

    PG_SCHEMA = """
    CREATE TABLE IF NOT EXISTS cloud_sessions (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        current_model TEXT,
        context_tokens INTEGER DEFAULT 0,
        created_at DOUBLE PRECISION NOT NULL,
        updated_at DOUBLE PRECISION NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb
    );

    CREATE TABLE IF NOT EXISTS cloud_timeline_events (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL REFERENCES cloud_sessions(session_id) ON DELETE CASCADE,
        seq INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        payload JSONB NOT NULL,
        created_at DOUBLE PRECISION NOT NULL,
        UNIQUE (session_id, seq)
    );

    CREATE INDEX IF NOT EXISTS idx_cloud_timeline_lookup 
    ON cloud_timeline_events(session_id, seq);
    """

    def __init__(self, dsn: Optional[str] = None) -> None:
        self.dsn = dsn
        self._driver: Optional[str] = None
        self._determine_driver()

    def _determine_driver(self) -> None:
        try:
            import psycopg2  # noqa: F401
            self._driver = "psycopg2"
        except ImportError:
            try:
                import pg8000  # noqa: F401
                self._driver = "pg8000"
            except ImportError:
                self._driver = None
                logger.warning("Neither psycopg2 nor pg8000 is installed. Postgres sync disabled.")

    def is_configured(self) -> bool:
        return bool(self.dsn and self._driver)

    def _sync_connect(self):
        if not self.dsn:
            raise ValueError("No PostgreSQL DSN configured.")
        if self._driver == "psycopg2":
            import psycopg2
            return psycopg2.connect(self.dsn, connect_timeout=5)
        elif self._driver == "pg8000":
            import socket
            import ssl
            import urllib.parse
            import pg8000.native

            p = urllib.parse.urlparse(self.dsn)
            host = p.hostname or "localhost"

            # Check if internal Render hostname requires external resolution fallback
            if host.startswith("dpg-") and "." not in host:
                try:
                    socket.gethostbyname(host)
                except socket.gaierror:
                    host = f"{host}.oregon-postgres.render.com"

            # Render PostgreSQL requires SSL
            ssl_ctx = None
            if "onrender.com" in host or "sslmode=require" in p.query or "ssl=true" in p.query or host.startswith("dpg-"):
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

            return pg8000.native.Connection(
                user=p.username or "postgres",
                password=p.password or "",
                host=host,
                port=p.port or 5432,
                database=p.path.lstrip("/") or "postgres",
                ssl_context=ssl_ctx,
                timeout=5,
            )
        raise RuntimeError("No suitable Postgres driver available.")

    async def ping(self) -> bool:
        """Check if Render Cloud PostgreSQL is reachable."""
        if not self.is_configured():
            return False

        def _ping_sync() -> bool:
            try:
                conn = self._sync_connect()
                if self._driver == "psycopg2":
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                    conn.close()
                else:
                    conn.run("SELECT 1;")
                    conn.close()
                return True
            except Exception as e:
                logger.debug("Render Postgres ping failed: %s", e)
                return False

        return await asyncio.to_thread(_ping_sync)

    async def init_schema(self) -> None:
        """Create cloud tables if they don't exist."""
        if not self.is_configured():
            return

        def _init_sync() -> None:
            conn = self._sync_connect()
            try:
                if self._driver == "psycopg2":
                    with conn.cursor() as cur:
                        cur.execute(self.PG_SCHEMA)
                    conn.commit()
                else:
                    for stmt in self.PG_SCHEMA.split(";"):
                        clean = stmt.strip()
                        if clean:
                            conn.run(clean)
            finally:
                conn.close()

        await asyncio.to_thread(_init_sync)

    async def upsert_session(self, session: Dict[str, Any]) -> None:
        if not self.is_configured():
            return

        def _upsert_sync() -> None:
            conn = self._sync_connect()
            try:
                meta = session.get("metadata", {})
                meta_json = json.dumps(meta) if isinstance(meta, dict) else str(meta)
                sql = """
                INSERT INTO cloud_sessions (session_id, title, status, current_model, context_tokens, created_at, updated_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (session_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    current_model = EXCLUDED.current_model,
                    context_tokens = EXCLUDED.context_tokens,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata;
                """
                params = (
                    session["session_id"],
                    session["title"],
                    session["status"],
                    session.get("current_model"),
                    session.get("context_tokens", 0),
                    session["created_at"],
                    session["updated_at"],
                    meta_json,
                )
                if self._driver == "psycopg2":
                    with conn.cursor() as cur:
                        cur.execute(sql, params)
                    conn.commit()
                else:
                    pg_sql, pg_kwargs = _format_pg8000_query(sql, params)
                    conn.run(pg_sql, **pg_kwargs)
            finally:
                conn.close()

        await asyncio.to_thread(_upsert_sync)

    async def batch_insert_events(self, events: List[Dict[str, Any]]) -> None:
        if not self.is_configured() or not events:
            return

        def _insert_sync() -> None:
            conn = self._sync_connect()
            try:
                sql = """
                INSERT INTO cloud_timeline_events (session_id, seq, event_type, payload, created_at)
                VALUES (%s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (session_id, seq) DO NOTHING;
                """
                if self._driver == "psycopg2":
                    with conn.cursor() as cur:
                        for ev in events:
                            payload_str = (
                                json.dumps(ev["payload"])
                                if isinstance(ev["payload"], dict)
                                else str(ev["payload"])
                            )
                            cur.execute(
                                sql,
                                (
                                    ev["session_id"],
                                    ev["seq"],
                                    ev["event_type"],
                                    payload_str,
                                    ev["created_at"],
                                ),
                            )
                    conn.commit()
                else:
                    for ev in events:
                        payload_str = (
                            json.dumps(ev["payload"])
                            if isinstance(ev["payload"], dict)
                            else str(ev["payload"])
                        )
                        ev_params = (
                            ev["session_id"],
                            ev["seq"],
                            ev["event_type"],
                            payload_str,
                            ev["created_at"],
                        )
                        pg_sql, pg_kwargs = _format_pg8000_query(sql, ev_params)
                        conn.run(pg_sql, **pg_kwargs)
            finally:
                conn.close()

        await asyncio.to_thread(_insert_sync)
