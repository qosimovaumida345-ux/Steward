"""
Main Application Window for Steward.
High-density multi-panel desktop client with real-time daemon synchronization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from qtpy.QtCore import Qt, QTimer, Slot
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from ..config.endpoints import resolve_server_endpoints
from ..config.settings import get_settings
from .components.approval_modal import ApprovalModal
from .components.diff_viewer import DiffViewerWidget
from .components.model_selector import ModelSelectorWidget
from .components.session_list import SessionListWidget
from .components.status_bar import AgentStatusBar
from .components.terminal_widget import TerminalWidget
from .components.timeline_view import TimelineViewWidget
from .worker_thread import DaemonClientThread

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window orchestrating developer workspaces and real-time streams."""

    def __init__(
        self,
        host: str = DEFAULT_DAEMON_HOST,
        port: int = DEFAULT_DAEMON_PORT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.host = host
        self.port = port
        self.http_base, self.ws_base = resolve_server_endpoints(host, port)
        self.current_session_id = "initial"

        self.setWindowTitle(f"Steward — Autonomous Developer Agent [{self.http_base}]")
        self.resize(1300, 850)

        self._build_ui()
        self._init_client_thread()
        self._refresh_sessions()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # 1. Top Control Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        logo = QLabel("Steward")
        logo.setStyleSheet("font-weight: 800; font-size: 14px; letter-spacing: 1px; color: #F8FAFC;")
        top_bar.addWidget(logo)

        self.model_selector = ModelSelectorWidget()
        top_bar.addWidget(self.model_selector)

        top_bar.addStretch()

        self.cancel_btn = QPushButton("Cancel Execution")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        top_bar.addWidget(self.cancel_btn)

        root_layout.addLayout(top_bar)

        # 2. Main Horizontal Splitter (Sidebar + Work Area)
        h_splitter = QSplitter(Qt.Horizontal)

        # Sidebar
        self.session_list = SessionListWidget()
        self.session_list.session_selected.connect(self._on_session_switched)
        self.session_list.new_session_requested.connect(self._on_new_session_requested)
        self.session_list.setMaximumWidth(280)
        h_splitter.addWidget(self.session_list)

        # Work Area (Vertical Splitter: Timeline Stream + Output Tabs)
        v_splitter = QSplitter(Qt.Vertical)

        # Top: Timeline Stream
        self.timeline_view = TimelineViewWidget()
        v_splitter.addWidget(self.timeline_view)

        # Bottom: Terminal & Diff Tabs
        self.bottom_tabs = QTabWidget()
        self.terminal_widget = TerminalWidget()
        self.diff_viewer = DiffViewerWidget()
        self.bottom_tabs.addTab(self.terminal_widget, "Terminal Console")
        self.bottom_tabs.addTab(self.diff_viewer, "File Diffs")
        v_splitter.addWidget(self.bottom_tabs)

        v_splitter.setStretchFactor(0, 3)
        v_splitter.setStretchFactor(1, 2)

        h_splitter.addWidget(v_splitter)
        h_splitter.setStretchFactor(1, 4)

        root_layout.addWidget(h_splitter)

        # 3. Bottom Prompt Input Bar
        prompt_bar = QHBoxLayout()
        prompt_bar.setSpacing(8)

        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Dispatch autonomous engineering task (e.g., 'Refactor storage and verify pytest')...")
        self.prompt_input.returnPressed.connect(self._on_dispatch_task)
        prompt_bar.addWidget(self.prompt_input)

        self.dispatch_btn = QPushButton("Dispatch Task")
        self.dispatch_btn.setObjectName("primaryButton")
        self.dispatch_btn.clicked.connect(self._on_dispatch_task)
        prompt_bar.addWidget(self.dispatch_btn)

        root_layout.addLayout(prompt_bar)

        # 4. Status Bar
        self.status_bar = AgentStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_client_thread(self) -> None:
        self.worker = DaemonClientThread(
            session_id=self.current_session_id,
            host=self.host,
            port=self.port,
            parent=self,
        )
        self.worker.event_received.connect(self._on_event_received)
        self.worker.connection_changed.connect(self.status_bar.set_connected)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    @Slot(str)
    def _on_worker_error(self, err: str) -> None:
        self.terminal_widget.append_output(f"[Daemon Alert] {err}\n")

    def _refresh_sessions(self) -> None:
        try:
            url = f"{self.http_base}/api/v1/sessions"
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    sessions = res.json().get("sessions", [])
                    self.session_list.update_sessions(sessions)
        except Exception as e:
            logger.debug("Failed to refresh sessions from %s: %s", self.http_base, e)

    @Slot(str)
    def _on_session_switched(self, session_id: str) -> None:
        self.current_session_id = session_id
        self.timeline_view.clear()
        self.terminal_widget.clear()
        self.diff_viewer.set_diff("")
        self.worker.switch_session(session_id)
        self.status_bar.set_seq(0)

    @Slot()
    def _on_new_session_requested(self) -> None:
        self.prompt_input.setFocus()

    @Slot()
    def _on_dispatch_task(self) -> None:
        task_text = self.prompt_input.text().strip()
        if not task_text:
            return

        self.prompt_input.clear()
        selected_model = self.model_selector.get_selected_model_id()

        try:
            url = f"{self.http_base}/api/v1/sessions"
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    url,
                    json={"task": task_text, "model": selected_model},
                )
                if resp.status_code == 201:
                    new_sid = resp.json().get("session_id")
                    if new_sid:
                        self._on_session_switched(new_sid)
                        self._refresh_sessions()
        except Exception as e:
            self.terminal_widget.append_output(f"Failed to dispatch task to server ({self.http_base}): {e}\n")

    @Slot()
    def _on_cancel_clicked(self) -> None:
        self.worker.send_cancel()

    @Slot(dict)
    def _on_event_received(self, event: Dict[str, Any]) -> None:
        event_type = event.get("event_type")
        seq = event.get("seq", 0)
        payload = event.get("payload", {})

        if seq:
            self.status_bar.set_seq(seq)

        if event_type == "thinking_chunk":
            chunk = payload.get("chunk", "")
            self.timeline_view.append_reasoning(chunk)

        elif event_type == "plan_generated":
            goal = payload.get("goal", "Plan Generated")
            steps = payload.get("steps", [])
            steps_desc = "\n".join(f"{s.get('step_id')}. {s.get('title')}" for s in steps)
            self.timeline_view.add_card(goal, "plan", steps_desc)

        elif event_type == "step_started":
            title = payload.get("title", "Step Started")
            desc = payload.get("description", "")
            self.timeline_view.add_card(f"Starting: {title}", "step", desc)

        elif event_type == "step_completed":
            sid = payload.get("step_id")
            result = payload.get("result", "Finished")
            self.timeline_view.add_card(f"Completed Step {sid}", "step", result)

        elif event_type == "terminal_output":
            cmd = payload.get("command", "")
            out = payload.get("output", "")
            self.terminal_widget.append_output(f"$ {cmd}\n{out}\n")

        elif event_type == "file_diff":
            diff = payload.get("diff", "")
            if diff:
                self.diff_viewer.set_diff(diff)
                self.bottom_tabs.setCurrentWidget(self.diff_viewer)

        elif event_type == "tool_call_requested":
            token = payload.get("approval_token")
            if token:
                # Show approval modal
                tool = payload.get("tool_name", "Tool")
                args = payload.get("arguments", {})
                reason = payload.get("reason", "Privileged operation")
                modal = ApprovalModal(token, tool, args, reason, self)
                modal.decision_made.connect(self.worker.send_approval)
                modal.show()

    def closeEvent(self, event) -> None:
        self.worker.stop()
        super().closeEvent(event)
