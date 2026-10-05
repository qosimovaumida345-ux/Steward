"""
Session Manager: Lifecycle supervisor for background autonomous agents.
Guarantees uninterrupted background execution when desktop client detaches.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from ..brain.dual_engine import DualEngineCoordinator
from ..brain.nvidia_client import NvidiaNimClient
from ..config.constants import PermissionMode, SessionState
from ..config.settings import get_settings
from ..core.agent_loop import AutonomousAgentLoop
from ..core.state_machine import SessionStateMachine
from ..core.timeline_journal import TimelineJournal
from ..security.approval_manager import ApprovalManager
from ..security.permission_guard import PermissionGuard
from ..storage.sqlite_store import SQLiteStore
from ..tools.computer_use_tools import (
    CaptureScreenTool,
    InspectWindowsTool,
    MouseClickTool,
    TypeTextTool,
    WinRtOcrTool,
)
from ..tools.file_tools import (
    FindByNameTool,
    GrepSearchTool,
    ListDirTool,
    ReplaceContentTool,
    ViewFileTool,
    WriteToFileTool,
)
from ..tools.registry import ToolRegistry
from ..tools.terminal_tools import RunCommandTool
from .notification_hub import NotificationHub
from .websocket_hub import WebSocketHub

logger = logging.getLogger(__name__)


class ActiveSession:
    def __init__(
        self,
        session_id: str,
        title: str,
        agent_loop: AutonomousAgentLoop,
        task_handle: asyncio.Task,
        approval_manager: ApprovalManager,
    ) -> None:
        self.session_id = session_id
        self.title = title
        self.agent_loop = agent_loop
        self.task_handle = task_handle
        self.approval_manager = approval_manager


class SessionManager:
    """Oversees all active and persisted agent sessions in the daemon."""

    def __init__(
        self,
        sqlite_store: SQLiteStore,
        ws_hub: WebSocketHub,
        notification_hub: Optional[NotificationHub] = None,
    ) -> None:
        self.sqlite = sqlite_store
        self.ws_hub = ws_hub
        self.notifier = notification_hub or NotificationHub()
        self._active_sessions: Dict[str, ActiveSession] = {}

    def _build_default_tool_registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        reg.register(ViewFileTool())
        reg.register(WriteToFileTool())
        reg.register(ReplaceContentTool())
        reg.register(ListDirTool())
        reg.register(GrepSearchTool())
        reg.register(FindByNameTool())
        reg.register(RunCommandTool())
        reg.register(CaptureScreenTool())
        reg.register(MouseClickTool())
        reg.register(TypeTextTool())
        reg.register(InspectWindowsTool())
        reg.register(WinRtOcrTool())
        return reg

    async def create_and_start_session(
        self,
        task: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        permission_mode: Optional[PermissionMode] = None,
    ) -> str:
        session_id = str(uuid.uuid4())[:12]
        session_title = title or (task[:40] + ("..." if len(task) > 40 else ""))

        # 1. Initialize SQLite Session Record
        self.sqlite.create_session(
            session_id=session_id,
            title=session_title,
            status=SessionState.IDLE.value,
            model=model or get_settings().planner_model,
        )

        # 2. Build session components
        state_machine = SessionStateMachine(SessionState.IDLE)
        approval_mgr = ApprovalManager()
        guard = PermissionGuard(
            mode=permission_mode or get_settings().permission_mode,
            approval_manager=approval_mgr,
        )
        tools = self._build_default_tool_registry()

        # Connect Timeline Journal with real-time broadcasting
        journal = TimelineJournal(session_id, self.sqlite)
        loop = asyncio.get_running_loop()

        def _on_journal_event(ev: Dict[str, Any]) -> None:
            # Broadcast to WebSocket clients
            asyncio.run_coroutine_threadsafe(
                self.ws_hub.broadcast_event(session_id, ev), loop
            )

        journal.add_listener(_on_journal_event)

        coordinator = DualEngineCoordinator()
        agent = AutonomousAgentLoop(
            session_id=session_id,
            journal=journal,
            state_machine=state_machine,
            tool_registry=tools,
            permission_guard=guard,
            coordinator=coordinator,
        )

        # 3. Launch background execution task
        bg_task = asyncio.create_task(self._run_session_background(agent, task, session_title))
        self._active_sessions[session_id] = ActiveSession(
            session_id=session_id,
            title=session_title,
            agent_loop=agent,
            task_handle=bg_task,
            approval_manager=approval_mgr,
        )

        logger.info("Created and launched active background session %s", session_id)
        return session_id

    async def _run_session_background(
        self, agent: AutonomousAgentLoop, task: str, title: str
    ) -> None:
        try:
            success = await agent.run(task)
            status = SessionState.COMPLETED.value if success else SessionState.FAILED.value
            self.sqlite.update_session_status(agent.session_id, status)
            if success:
                await self.notifier.notify_task_complete(agent.session_id, title)
        except asyncio.CancelledError:
            self.sqlite.update_session_status(agent.session_id, SessionState.TERMINATED.value)
        except Exception as e:
            logger.exception("Session %s encountered fatal error: %s", agent.session_id, e)
            self.sqlite.update_session_status(agent.session_id, SessionState.FAILED.value)

    def cancel_session(self, session_id: str) -> bool:
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        session.agent_loop.cancel()
        session.task_handle.cancel()
        self.sqlite.update_session_status(session_id, SessionState.TERMINATED.value)
        return True

    def resolve_approval(self, session_id: str, token: str, approved: bool) -> bool:
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        return session.approval_manager.resolve_request(token, approved)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self.sqlite.list_sessions(limit=50)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sqlite.get_session(session_id)
