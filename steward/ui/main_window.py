"""
Main Application Window for Steward.
Antigravity 2.0 / Cursor IDE inspired multi-panel developer environment:
- Project folder explorer & file tree navigation
- Conversational chat interface with live DeepSeek CoT thinking disclosures
- Multi-line chat composer with integrated model selection
- Code viewer, file diff inspector, and live terminal console
- Non-blocking asynchronous daemon & Render cloud synchronization
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

import httpx
from qtpy.QtCore import Qt, QTimer, Signal, Slot
from qtpy.QtGui import QKeySequence, QShortcut
from qtpy.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT, DEFAULT_SERVER_URL
from ..config.endpoints import resolve_server_endpoints
from ..config.settings import get_settings
from .components.approval_modal import ApprovalModal
from .components.chat_composer import ChatComposerWidget
from .components.chat_view import ChatViewWidget
from .components.code_viewer import CodeViewerWidget
from .components.diff_viewer import DiffViewerWidget
from .components.model_selector import ModelSelectorWidget
from .components.project_explorer import ProjectExplorerWidget
from .components.session_list import SessionListWidget
from .components.status_bar import AgentStatusBar
from .components.terminal_widget import TerminalWidget
from .worker_thread import DaemonClientThread

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Antigravity 2.0 developer IDE window orchestrating agents, files, and chat streams."""

    dispatch_finished = Signal(str, str)
    sessions_loaded = Signal(list)
    session_events_loaded = Signal(str, list)

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        workspace_dir: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        settings = get_settings()
        self.host = host or settings.server_url or DEFAULT_SERVER_URL
        self.port = port if port is not None else settings.daemon_port
        self.http_base, self.ws_base = resolve_server_endpoints(self.host, self.port)

        self.workspace_dir = Path(workspace_dir or os.getcwd()).resolve()
        self.current_session_id = "initial"
        self._is_running_task = False

        self.setWindowTitle(f"Steward 2.0 — Autonomous Developer Agent [{self.workspace_dir.name}]")
        self.resize(1400, 900)

        self._build_ui()
        self._init_signals()
        self._init_shortcuts()
        self._init_client_thread()

        # Non-blocking initial session refresh
        QTimer.singleShot(50, self._refresh_sessions)

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        # ---------------- 1. Top Navigation & Activity Bar ----------------
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 2, 4, 4)
        top_bar.setSpacing(10)

        # Brand Logo
        logo = QLabel("STEWARD 2.0")
        logo.setStyleSheet(
            "font-weight: 900; font-size: 14px; letter-spacing: 1.5px; color: #60A5FA; padding: 2px 4px;"
        )
        top_bar.addWidget(logo)

        # Workspace Directory Button
        self.workspace_btn = QPushButton(f"📁 {self.workspace_dir.name}")
        self.workspace_btn.setObjectName("ghostButton")
        self.workspace_btn.setToolTip(f"Workspace: {self.workspace_dir}\nClick to change folder")
        self.workspace_btn.clicked.connect(self._on_change_workspace)
        top_bar.addWidget(self.workspace_btn)

        top_bar.addStretch()

        # Server Status Badge
        self.server_badge = QLabel(f"Server: {self.http_base}")
        self.server_badge.setStyleSheet(
            "color: #94A3B8; background: #0E1626; border: 1px solid #1E293B; "
            "font-size: 11px; padding: 3px 8px; border-radius: 4px;"
        )
        top_bar.addWidget(self.server_badge)

        # Sidebar Toggle Button
        self.toggle_sidebar_btn = QPushButton("Sidebar")
        self.toggle_sidebar_btn.setObjectName("ghostButton")
        self.toggle_sidebar_btn.setToolTip("Toggle sidebar visibility (Ctrl+B)")
        self.toggle_sidebar_btn.clicked.connect(self._toggle_sidebar)
        top_bar.addWidget(self.toggle_sidebar_btn)

        # Inspector Toggle Button
        self.toggle_inspector_btn = QPushButton("Inspector")
        self.toggle_inspector_btn.setObjectName("ghostButton")
        self.toggle_inspector_btn.setToolTip("Toggle inspector panel (Ctrl+J)")
        self.toggle_inspector_btn.clicked.connect(self._toggle_inspector)
        top_bar.addWidget(self.toggle_inspector_btn)

        root_layout.addLayout(top_bar)

        # ---------------- 2. Main Horizontal Splitter ----------------
        self.main_splitter = QSplitter(Qt.Horizontal)

        # --- A. Left Sidebar: Project Explorer & Sessions ---
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setMaximumWidth(360)
        self.sidebar_tabs.setMinimumWidth(220)

        self.project_explorer = ProjectExplorerWidget(root_path=str(self.workspace_dir))
        self.project_explorer.file_selected.connect(self._on_file_selected)
        self.project_explorer.reference_in_chat.connect(self._on_file_reference_requested)
        self.project_explorer.workspace_changed.connect(self._on_workspace_changed_from_explorer)

        self.session_list = SessionListWidget()
        self.session_list.session_selected.connect(self._on_session_switched)
        self.session_list.new_session_requested.connect(self._on_new_session_requested)
        self.session_list.refresh_requested.connect(self._refresh_sessions)

        self.sidebar_tabs.addTab(self.project_explorer, "Files")
        self.sidebar_tabs.addTab(self.session_list, "Chats")
        self.main_splitter.addWidget(self.sidebar_tabs)

        # --- B. Center Work Area: Antigravity Chat & Composer ---
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        self.chat_view = ChatViewWidget()
        self.chat_view.prompt_suggested.connect(self._on_prompt_suggested)
        center_layout.addWidget(self.chat_view, 1)

        self.chat_composer = ChatComposerWidget()
        self.chat_composer.dispatch_requested.connect(self._on_dispatch_task)
        self.chat_composer.cancel_requested.connect(self._on_cancel_clicked)
        center_layout.addWidget(self.chat_composer)

        self.main_splitter.addWidget(center_container)

        # --- C. Right Inspector: Code Viewer, Diffs, Terminal ---
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setMinimumWidth(320)

        self.code_viewer = CodeViewerWidget()
        self.diff_viewer = DiffViewerWidget()
        self.terminal_widget = TerminalWidget()

        self.inspector_tabs.addTab(self.code_viewer, "Code Preview")
        self.inspector_tabs.addTab(self.diff_viewer, "File Diffs")
        self.inspector_tabs.addTab(self.terminal_widget, "Terminal")

        self.main_splitter.addWidget(self.inspector_tabs)

        # Set Splitter Ratios: Sidebar (20%), Chat (50%), Inspector (30%)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 5)
        self.main_splitter.setStretchFactor(2, 3)

        root_layout.addWidget(self.main_splitter, 1)

        # ---------------- 3. Status Bar ----------------
        self.status_bar = AgentStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_signals(self) -> None:
        self.sessions_loaded.connect(self.session_list.update_sessions)
        self.session_events_loaded.connect(self._on_session_events_loaded)
        self.dispatch_finished.connect(self._on_dispatch_finished)

    def _init_shortcuts(self) -> None:
        # Ctrl+B: Toggle Sidebar
        shortcut_sidebar = QShortcut(QKeySequence("Ctrl+B"), self)
        shortcut_sidebar.activated.connect(self._toggle_sidebar)

        # Ctrl+J: Toggle Inspector
        shortcut_inspector = QShortcut(QKeySequence("Ctrl+J"), self)
        shortcut_inspector.activated.connect(self._toggle_inspector)

    def _init_client_thread(self) -> None:
        self.worker = DaemonClientThread(
            session_id=self.current_session_id,
            host=self.host,
            port=self.port,
            parent=self,
        )
        self.worker.event_received.connect(self._on_event_received)
        self.worker.connection_changed.connect(self._on_connection_changed)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

        # Periodic background refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_sessions)
        self._refresh_timer.start(15000)

    # ---------------- Workspace & File Handlers ----------------

    def _on_change_workspace(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Select Workspace Folder",
            str(self.workspace_dir),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if chosen:
            self._update_workspace(Path(chosen))

    def _update_workspace(self, path: Path) -> None:
        self.workspace_dir = path.resolve()
        self.workspace_btn.setText(f"📁 {self.workspace_dir.name}")
        self.workspace_btn.setToolTip(f"Workspace: {self.workspace_dir}")
        self.setWindowTitle(f"Steward 2.0 — Autonomous Developer Agent [{self.workspace_dir.name}]")
        self.project_explorer.set_workspace(str(self.workspace_dir))

    def _on_workspace_changed_from_explorer(self, path_str: str) -> None:
        target = Path(path_str).resolve()
        self.workspace_dir = target
        self.workspace_btn.setText(f"📁 {self.workspace_dir.name}")
        self.workspace_btn.setToolTip(f"Workspace: {self.workspace_dir}")
        self.setWindowTitle(f"Steward 2.0 — Autonomous Developer Agent [{self.workspace_dir.name}]")

    def _on_file_selected(self, file_path: str) -> None:
        self.code_viewer.load_file(file_path)
        self.inspector_tabs.setCurrentWidget(self.code_viewer)

    def _on_file_reference_requested(self, ref_str: str) -> None:
        self.chat_composer.insert_text(ref_str)

    def _on_prompt_suggested(self, prompt_text: str) -> None:
        self.chat_composer.insert_text(prompt_text)

    # ---------------- View Toggle Handlers ----------------

    def _toggle_sidebar(self) -> None:
        self.sidebar_tabs.setVisible(not self.sidebar_tabs.isVisible())

    def _toggle_inspector(self) -> None:
        self.inspector_tabs.setVisible(not self.inspector_tabs.isVisible())

    # ---------------- Network & Session Handlers ----------------

    @Slot(bool)
    def _on_connection_changed(self, is_connected: bool) -> None:
        self.status_bar.set_connected(is_connected)
        if is_connected:
            self.server_badge.setText(f"🟢 Connected: {self.http_base}")
            self.server_badge.setStyleSheet(
                "color: #34D399; background: #064E3B; border: 1px solid #059669; "
                "font-size: 11px; padding: 3px 8px; border-radius: 4px;"
            )
            self._refresh_sessions()
        else:
            self.server_badge.setText(f"🟡 Detached: {self.http_base}")
            self.server_badge.setStyleSheet(
                "color: #FCD34D; background: #451A03; border: 1px solid #D97706; "
                "font-size: 11px; padding: 3px 8px; border-radius: 4px;"
            )

    @Slot(str)
    def _on_worker_error(self, err: str) -> None:
        self.terminal_widget.append_output(f"[Daemon Alert] {err}\n")

    def _refresh_sessions(self) -> None:
        """Fetch sessions asynchronously in background thread."""
        def _fetch():
            try:
                url = f"{self.http_base}/api/v1/sessions"
                with httpx.Client(timeout=10.0) as client:
                    res = client.get(url)
                    if res.status_code == 200:
                        sessions = res.json().get("sessions", [])
                        self.sessions_loaded.emit(sessions)
            except Exception as e:
                logger.debug("Failed to refresh sessions from %s: %s", self.http_base, e)

        threading.Thread(target=_fetch, daemon=True).start()

    @Slot(str)
    def _on_session_switched(self, session_id: str) -> None:
        """User switched active session in sidebar."""
        self.current_session_id = session_id
        self.chat_view.clear()
        self.chat_view.set_session_info(session_id)
        self.terminal_widget.clear()
        self.diff_viewer.set_diff("")
        self.worker.switch_session(session_id)
        self.status_bar.set_seq(0)

        # Load past events for this session
        def _fetch_events():
            try:
                url = f"{self.http_base}/api/v1/sessions/{session_id}/events?limit=200"
                with httpx.Client(timeout=10.0) as client:
                    res = client.get(url)
                    if res.status_code == 200:
                        events = res.json().get("events", [])
                        self.session_events_loaded.emit(session_id, events)
            except Exception as e:
                logger.debug("Failed to load session events for %s: %s", session_id, e)

        threading.Thread(target=_fetch_events, daemon=True).start()

    @Slot(str, list)
    def _on_session_events_loaded(self, session_id: str, events: List[Dict[str, Any]]) -> None:
        """Replay loaded history events into chat and inspector tabs."""
        if session_id != self.current_session_id:
            return

        for ev in events:
            self._process_event(ev, is_replay=True)

    @Slot()
    def _on_new_session_requested(self) -> None:
        """Start a new clean chat view."""
        self.chat_view.clear()
        self.chat_view.set_session_info("New Chat", "Ready")
        self.terminal_widget.clear()
        self.diff_viewer.set_diff("")
        self.current_session_id = "new"
        self.chat_composer.editor.setFocus()

    @Slot(str, str)
    def _on_dispatch_task(self, task_text: str, selected_model: str) -> None:
        """User clicked Send or pressed Enter in chat composer."""
        if not task_text:
            return

        # Add user message bubble to chat view immediately
        self.chat_view.add_user_message(task_text)
        self.chat_view.start_agent_response(selected_model)
        self.chat_composer.set_running(True)
        self._is_running_task = True

        self.terminal_widget.append_output(f"[Client] Dispatching task with model '{selected_model}' to {self.http_base}...\n")

        def _dispatch():
            try:
                url = f"{self.http_base}/api/v1/sessions"
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(
                        url,
                        json={
                            "task": task_text,
                            "model": selected_model,
                            "workspace": str(self.workspace_dir),
                        },
                    )
                    if resp.status_code == 201:
                        new_sid = resp.json().get("session_id", "")
                        self.dispatch_finished.emit("success", new_sid)
                        return
                    self.dispatch_finished.emit("error", f"HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                self.dispatch_finished.emit("error", str(e))

        threading.Thread(target=_dispatch, daemon=True).start()

    @Slot(str, str)
    def _on_dispatch_finished(self, status: str, payload: str) -> None:
        if status == "success":
            self.terminal_widget.append_output(f"[Client] Session started: {payload}\n")
            self.current_session_id = payload
            self.chat_view.set_session_info(payload)
            self.worker.switch_session(payload)
            self._refresh_sessions()
        else:
            self.chat_composer.set_running(False)
            self._is_running_task = False
            self.chat_view.add_tool_execution(
                "dispatch_error",
                "Failed to dispatch task to server",
                output=payload,
                status="error",
            )
            self.terminal_widget.append_output(f"[Client Error] Failed to dispatch task: {payload}\n")

    @Slot()
    def _on_cancel_clicked(self) -> None:
        self.worker.send_cancel()
        self.chat_composer.set_running(False)
        self._is_running_task = False
        self.chat_view.finish_agent_response("Cancelled by user")
        self.terminal_widget.append_output("[Client] Task cancelled by user.\n")

    # ---------------- Live Stream Event Processing ----------------

    @Slot(dict)
    def _on_event_received(self, event: Dict[str, Any]) -> None:
        self._process_event(event, is_replay=False)

    def _process_event(self, event: Dict[str, Any], is_replay: bool = False) -> None:
        event_type = event.get("event_type")
        seq = event.get("seq", 0)
        payload = event.get("payload", {})

        if seq:
            self.status_bar.set_seq(seq)

        if event_type == "thinking_chunk":
            chunk = payload.get("chunk", "")
            self.chat_view.append_reasoning(chunk)

        elif event_type == "plan_generated":
            goal = payload.get("goal", "Execution Plan")
            steps = payload.get("steps", [])
            self.chat_view.add_plan(goal, steps)

        elif event_type == "step_started":
            title = payload.get("title", "Step Started")
            sid = payload.get("step_id", 0)
            self.terminal_widget.append_output(f"[Step {sid}] Starting: {title}\n")

        elif event_type == "step_completed":
            sid = payload.get("step_id", 0)
            result = payload.get("result", "Completed")
            self.terminal_widget.append_output(f"[Step {sid}] Finished: {result}\n")

        elif event_type == "terminal_output":
            cmd = payload.get("command", "")
            out = payload.get("output", "")
            self.chat_view.add_tool_execution("run_command", cmd, output=out, status="success")
            self.terminal_widget.append_output(f"$ {cmd}\n{out}\n")

        elif event_type == "file_diff":
            diff = payload.get("diff", "")
            if diff:
                self.diff_viewer.set_diff(diff)
                if not is_replay:
                    self.inspector_tabs.setCurrentWidget(self.diff_viewer)

        elif event_type == "tool_call_requested":
            token = payload.get("approval_token")
            if token:
                tool = payload.get("tool_name", "Tool")
                args = payload.get("arguments", {})
                reason = payload.get("reason", "Privileged operation")
                modal = ApprovalModal(token, tool, args, reason, self)
                modal.decision_made.connect(self.worker.send_approval)
                modal.show()

        elif event_type == "status_changed":
            status = payload.get("status", "")
            summary = payload.get("summary", "")
            if status in ("COMPLETED", "FAILED", "TERMINATED"):
                self.chat_composer.set_running(False)
                self._is_running_task = False
                color = "#10B981" if status == "COMPLETED" else "#EF4444"
                self.chat_view.finish_agent_response(f"{status}: {summary}" if summary else status)

    def closeEvent(self, event) -> None:
        if hasattr(self, "_refresh_timer") and self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self.worker.stop()
        super().closeEvent(event)
