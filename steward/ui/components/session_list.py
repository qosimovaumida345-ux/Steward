"""
Session List & Skills Explorer Sidebar Component.
Provides tree navigation of active sessions, subagent delegates, and progressive skills.
"""

from __future__ import annotations

from typing import Any, Dict, List
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        new_btn = QPushButton("+ New Task")
        new_btn.setObjectName("primaryButton")
        new_btn.clicked.connect(self.new_session_requested.emit)
        btn_row.addWidget(new_btn, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setToolTip("Reload sessions from server")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        btn_row.addWidget(refresh_btn)

        layout.addLayout(btn_row)

        self.tabs = QTabWidget()

        # Tab 1: Sessions
        self.session_tree = QTreeWidget()
        self.session_tree.setHeaderHidden(True)
        self.session_tree.itemClicked.connect(self._on_item_clicked)
        self.tabs.addTab(self.session_tree, "Sessions")

        # Tab 2: Skills Explorer
        self.skills_tree = QTreeWidget()
        self.skills_tree.setHeaderHidden(True)
        self.tabs.addTab(self.skills_tree, "Skills")

        layout.addWidget(self.tabs)

    def update_sessions(self, sessions: List[Dict[str, Any]]) -> None:
        self.session_tree.clear()
        for s in sessions:
            sid = s.get("session_id", "unknown")
            title = s.get("title", sid)
            status = s.get("status", "IDLE")

            status_color = "#10B981" if status == "COMPLETED" else "#3B82F6" if status == "RUNNING" else "#64748B"
            item = QTreeWidgetItem([f"[{status}] {title}"])
            item.setData(0, 100, sid)
            self.session_tree.addTopLevelItem(item)

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
