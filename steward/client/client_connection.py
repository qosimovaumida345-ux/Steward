"""
Daemon Client Connection.
Maintains resilient WebSocket connection to the Headless Cloud Daemon with auto-reconnect
and sequence catch-up synchronization.
Supports both local daemon (ws://) and Render Cloud (wss://) endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

import aiohttp

from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from ..config.endpoints import resolve_server_endpoints

logger = logging.getLogger(__name__)


class DaemonClientConnection:
    """Manages real-time WebSocket connection to the daemon for a specific session."""

    def __init__(
        self,
        session_id: str,
        host: str = DEFAULT_DAEMON_HOST,
        port: int = DEFAULT_DAEMON_PORT,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connection_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.session_id = session_id
        self.host = host
        self.port = port
        self.http_base, self.ws_base = resolve_server_endpoints(host, port)
        self.on_event = on_event
        self.on_connection_change = on_connection_change

        self.last_seq = 0
        self.is_connected = False
        self._running = False
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._task: Optional[asyncio.Task] = None

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the background connection loop."""
        if self._running:
            return
        self._running = True

        if loop is not None:
            self._task = loop.create_task(self._connection_loop())
        else:
            try:
                running_loop = asyncio.get_running_loop()
                self._task = running_loop.create_task(self._connection_loop())
            except RuntimeError:
                try:
                    event_loop = asyncio.get_event_loop()
                    self._task = event_loop.create_task(self._connection_loop())
                except RuntimeError:
                    self._task = None

    async def stop(self) -> None:
        """Gracefully disconnect and terminate loop."""
        self._running = False
        if self._ws and not self._ws.closed:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self._set_connected(False)

    def _set_connected(self, status: bool) -> None:
        if self.is_connected != status:
            self.is_connected = status
            if self.on_connection_change:
                try:
                    self.on_connection_change(status)
                except Exception as e:
                    logger.debug("Error in connection_change callback: %s", e)

    async def _connection_loop(self) -> None:
        url = f"{self.ws_base}/api/v1/sessions/{self.session_id}/ws"

        while self._running:
            try:
                timeout = aiohttp.ClientTimeout(total=60.0)
                self._session = aiohttp.ClientSession(timeout=timeout)
                async with self._session.ws_connect(url, heartbeat=30.0) as ws:
                    self._ws = ws
                    self._set_connected(True)
                    logger.info("Connected to daemon for session %s at %s (attaching seq %d)", self.session_id, url, self.last_seq)

                    # Send attach message with our latest sequence number
                    await ws.send_json({"type": "attach", "last_seq": self.last_seq})

                    async for msg in ws:
                        if not self._running:
                            break
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                seq = data.get("seq")
                                if seq and seq > self.last_seq:
                                    self.last_seq = seq

                                if self.on_event:
                                    self.on_event(data)
                            except Exception as e:
                                logger.error("Error processing incoming event: %s", e)

                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Daemon connection attempt failed to %s: %s", url, e)
            finally:
                self._set_connected(False)
                if self._session and not self._session.closed:
                    try:
                        await self._session.close()
                    except Exception:
                        pass

            if self._running:
                await asyncio.sleep(2.0)

    async def send_approval(self, token: str, approved: bool) -> None:
        if self._ws and not self._ws.closed:
            try:
                await self._ws.send_json({
                    "type": "approval_response",
                    "token": token,
                    "approved": approved,
                })
            except Exception as e:
                logger.warning("Failed to send approval response: %s", e)

    async def send_cancel(self) -> None:
        if self._ws and not self._ws.closed:
            try:
                await self._ws.send_json({"type": "cancel"})
            except Exception as e:
                logger.warning("Failed to send cancel: %s", e)
