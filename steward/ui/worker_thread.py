"""
Daemon Client Worker Thread (QThread).
Executes asynchronous WebSocket communications in a background thread and emits
thread-safe Qt Signals to update the UI without dropping frames.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from qtpy.QtCore import QThread, Signal, Slot

from ..client.client_connection import DaemonClientConnection
from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT

logger = logging.getLogger(__name__)


class DaemonClientThread(QThread):
    """
    QThread running an independent asyncio event loop connecting to the daemon's WebSocket endpoint.
    All incoming updates are marshalled across Qt thread boundaries via Signals.
    """

    event_received = Signal(dict)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(
        self,
        session_id: str,
        host: str = DEFAULT_DAEMON_HOST,
        port: int = DEFAULT_DAEMON_PORT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.session_id = session_id
        self.host = host
        self.port = port

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._connection: Optional[DaemonClientConnection] = None
        self._is_running = True

    def run(self) -> None:
        """Entry point executed on the secondary background thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            self._connection = DaemonClientConnection(
                session_id=self.session_id,
                host=self.host,
                port=self.port,
                on_event=self._handle_event,
                on_connection_change=self._handle_connection_change,
            )

            self._connection.start(loop=self._loop)
            self._loop.run_forever()
        except Exception as e:
            logger.error("DaemonClientThread error: %s", e, exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            if self._loop and not self._loop.is_closed():
                try:
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        self._loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                try:
                    self._loop.close()
                except Exception:
                    pass

    def _handle_event(self, event: Dict[str, Any]) -> None:
        self.event_received.emit(event)

    def _handle_connection_change(self, is_connected: bool) -> None:
        self.connection_changed.emit(is_connected)

    def send_approval(self, token: str, approved: bool) -> None:
        if self._loop and self._connection and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._connection.send_approval(token, approved), self._loop
            )

    def send_cancel(self) -> None:
        if self._loop and self._connection and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._connection.send_cancel(), self._loop
            )

    def switch_session(self, new_session_id: str) -> None:
        """Switch listening to a different session."""
        if not self._loop or not self._loop.is_running():
            self.session_id = new_session_id
            return

        async def _switch():
            if self._connection:
                await self._connection.stop()
            self.session_id = new_session_id
            self._connection = DaemonClientConnection(
                session_id=self.session_id,
                host=self.host,
                port=self.port,
                on_event=self._handle_event,
                on_connection_change=self._handle_connection_change,
            )
            self._connection.start(loop=self._loop)

        asyncio.run_coroutine_threadsafe(_switch(), self._loop)

    def stop(self) -> None:
        """Gracefully terminate client thread."""
        self._is_running = False
        if self._loop and self._loop.is_running():
            if self._connection:
                future = asyncio.run_coroutine_threadsafe(self._connection.stop(), self._loop)
                try:
                    future.result(timeout=2.0)
                except Exception:
                    pass
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(3000)
