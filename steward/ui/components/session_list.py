"""
Session List & Skills Explorer Sidebar Component.
Antigravity 2.0 styled sidebar for managing sessions, past tasks, and progressive skills.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SessionListWidget(QWidget):
    """Sidebar widget managing sessions, subagents, and skills."""

    session_selected = Signal(str)
    new_session_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._raw_sessions: List[Dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Header Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        new_btn = QPushButton("+ New Chat")
        new_btn.setObjectName("primaryButton")
        new_btn.setToolTip("Start a new agent session")
        new_btn.clicked.connect(self.new_session_requested.emit)
        btn_row.addWidget(new_btn, 1)

        refresh_btn = QPushButton("↺")
        refresh_btn.setObjectName("ghostButton")
        refresh_btn.setFixedWidth(28)
        refresh_btn.setToolTip("Reload sessions from server")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        btn_row.addWidget(refresh_btn)

        layout.addLayout(btn_row)

        # Search / Filter Box
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchFilter")
        self.search_input.setPlaceholderText("Filter sessions...")
        self.search_input.textChanged.connect(self._filter_sessions)
        layout.addWidget(self.search_input)

        self.tabs = QTabWidget()

        # Tab 1: Sessions
        self.session_tree = QTreeWidget()
        self.session_tree.setHeaderHidden(True)
        self.session_tree.setIndentation(10)
        self.session_tree.itemClicked.connect(self._on_item_clicked)
        self.tabs.addTab(self.session_tree, "Sessions")

        # Tab 2: Skills Explorer
        self.skills_tree = QTreeWidget()
        self.skills_tree.setHeaderHidden(True)
        self.tabs.addTab(self.skills_tree, "Skills")

        layout.addWidget(self.tabs)

    def update_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        self._raw_sessions = sessions
        self._render_sessions()

    def _render_sessions(self) -> None:
        self.session_tree.clear()
        filter_text = self.search_input.text().strip().lower()

        for s in self._raw_sessions:
            sid = s.get("session_id", "unknown")
            title = s.get("title", sid)
            status = s.get("status", "IDLE")

            if filter_text and filter_text not in title.lower() and filter_text not in sid.lower():
                continue

            status_icon = "●" if status == "RUNNING" else "✓" if status == "COMPLETED" else "○"
            item = QTreeWidgetItem([f"{status_icon}  {title}"])
            item.setToolTip(0, f"ID: {sid}\nStatus: {status}")
            item.setData(0, 100, sid)
            self.session_tree.addTopLevelItem(item)

    def _filter_sessions(self, text: str) -> None:
        self._render_sessions()

    def update_skills(self, skills: List[Dict[str, Any]]) -> None:
        self.skills_tree.clear()
        for sk in skills:
            item = QTreeWidgetItem([sk.get("name", "Skill")])
            item.setToolTip(0, sk.get("description", ""))
            self.skills_tree.addTopLevelItem(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        sid = item.data(0, 100)
        if sid:
            self.session_selected.emit(sid)
