"""
Headless Cloud Daemon HTTP & WebSocket Server.
Built on aiohttp to manage REST routes, WebSocket attach/detach, and Outbox replication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from aiohttp import web, WSMsgType

from ..brain.model_catalog import ModelCatalog
from ..brain.nvidia_client import NvidiaNimClient
from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from ..config.settings import get_settings
from ..storage.render_postgres import RenderPostgresClient
from ..storage.sqlite_store import SQLiteStore
from ..storage.sync_outbox import SyncOutboxWorker
from .notification_hub import NotificationHub
from .session_manager import SessionManager
from .websocket_hub import WebSocketHub

logger = logging.getLogger(__name__)


def create_daemon_app(
    sqlite_store: Optional[SQLiteStore] = None,
    render_client: Optional[RenderPostgresClient] = None,
) -> web.Application:
    """Create and configure the aiohttp web application for the daemon."""
    app = web.Application()

    # Shared instances
    store = sqlite_store or SQLiteStore()
    ws_hub = WebSocketHub(store)
    notifier = NotificationHub()
    session_mgr = SessionManager(store, ws_hub, notifier)
    nim_client = NvidiaNimClient()
    outbox_worker = SyncOutboxWorker(
        sqlite_store=store,
        postgres_client=render_client or RenderPostgresClient(get_settings().render_postgres_dsn),
    )

    app["sqlite_store"] = store
    app["ws_hub"] = ws_hub
    app["session_mgr"] = session_mgr
    app["nim_client"] = nim_client
    app["outbox_worker"] = outbox_worker

    # Lifecycle hooks
    async def on_startup(app_instance: web.Application) -> None:
        if get_settings().render_sync_enabled:
            await outbox_worker.start()
        logger.info("Steward Daemon started.")

    async def on_cleanup(app_instance: web.Application) -> None:
        await outbox_worker.stop()
        store.close()
        logger.info("Steward Daemon stopped.")

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    # ---------------- REST Route Handlers ----------------

    async def health_handler(request: web.Request) -> web.Response:
        return web.json_response({
            "status": "healthy",
            "version": "2.0.0",
            "service": "Steward Cloud Daemon",
        })

    async def list_models_handler(request: web.Request) -> web.Response:
        models = await nim_client.list_models()
        return web.json_response({"models": models})

    async def list_sessions_handler(request: web.Request) -> web.Response:
        sessions = session_mgr.list_sessions()
        return web.json_response({"sessions": sessions})

    async def create_session_handler(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON body"}, status=400)

        task = body.get("task")
        if not task:
            return web.json_response({"error": "Field 'task' is required"}, status=400)

        title = body.get("title")
        model = body.get("model")

        session_id = await session_mgr.create_and_start_session(task=task, title=title, model=model)
        return web.json_response({"session_id": session_id, "status": "started"}, status=201)

    async def get_session_handler(request: web.Request) -> web.Response:
        session_id = request.match_info["session_id"]
        sess = session_mgr.get_session(session_id)
        if not sess:
            return web.json_response({"error": "Session not found"}, status=404)
        return web.json_response({"session": sess})

    async def cancel_session_handler(request: web.Request) -> web.Response:
        session_id = request.match_info["session_id"]
        success = session_mgr.cancel_session(session_id)
        return web.json_response({"success": success})

    async def approval_handler(request: web.Request) -> web.Response:
        session_id = request.match_info["session_id"]
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        token = body.get("token")
        approved = body.get("approved", False)
        if not token:
            return web.json_response({"error": "Token required"}, status=400)

        res = session_mgr.resolve_approval(session_id, token, approved)
        return web.json_response({"success": res})

    async def events_catchup_handler(request: web.Request) -> web.Response:
        session_id = request.match_info["session_id"]
        last_seq = int(request.query.get("last_seq", "0"))
        limit = int(request.query.get("limit", "100"))
        events = store.get_timeline_events(session_id, after_seq=last_seq, limit=limit)
        return web.json_response({"session_id": session_id, "events": events})

    # ---------------- WebSocket Handler ----------------

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        session_id = request.match_info["session_id"]
        ws = web.WebSocketResponse(heartbeat=30.0)
        await ws.prepare(request)

        await ws_hub.register_connection(session_id, ws)

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue

                    msg_type = data.get("type")

                    # Handle attach & catch-up replay
                    if msg_type == "attach":
                        last_seq = data.get("last_seq", 0)
                        await ws_hub.replay_catch_up(ws, session_id, last_seq=last_seq)

                    # Handle interactive approval
                    elif msg_type == "approval_response":
                        token = data.get("token")
                        approved = data.get("approved", False)
                        if token:
                            session_mgr.resolve_approval(session_id, token, approved)

                    # Handle cancel
                    elif msg_type == "cancel":
                        session_mgr.cancel_session(session_id)

                elif msg.type == WSMsgType.ERROR:
                    logger.debug("WebSocket connection closed with error: %s", ws.exception())
        finally:
            await ws_hub.unregister_connection(session_id, ws)

        return ws

    # Add routes
    app.router.add_get("/health", health_handler)
    app.router.add_get("/api/v1/models", list_models_handler)
    app.router.add_get("/api/v1/sessions", list_sessions_handler)
    app.router.add_post("/api/v1/sessions", create_session_handler)
    app.router.add_get("/api/v1/sessions/{session_id}", get_session_handler)
    app.router.add_post("/api/v1/sessions/{session_id}/cancel", cancel_session_handler)
    app.router.add_post("/api/v1/sessions/{session_id}/approval", approval_handler)
    app.router.add_get("/api/v1/sessions/{session_id}/events", events_catchup_handler)
    app.router.add_get("/api/v1/sessions/{session_id}/ws", websocket_handler)

    return app


def run_daemon_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """Entrypoint function to run the daemon server."""
    settings = get_settings()
    h = host or settings.daemon_host
    p = port or settings.daemon_port
    app = create_daemon_app()
    logger.info("Starting Steward Daemon on http://%s:%d", h, p)
    web.run_app(app, host=h, port=p)
