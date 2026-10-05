"""
Timeline View Component: Agent Reasoning Stream & Tool Invocation Cards.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TimelineEventCard(QFrame):
    """Card representing a single step, reasoning block, or tool outcome."""

    def __init__(self, title: str, category: str, content: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panelFrame")
        self.setStyleSheet("""
            QFrame#panelFrame {
                background-color: #111726;
                border: 1px solid #1F293D;
                border-radius: 4px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_label = QLabel(title)
        header_label.setStyleSheet("font-weight: 600; color: #F1F5F9; font-size: 12px;")

        badge = QLabel(category.upper())
        cat_color = "#3B82F6" if category == "tool" else "#8B5CF6" if category == "reasoning" else "#10B981"
        badge.setStyleSheet(f"background: {cat_color}; color: #FFFFFF; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 3px;")

        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(badge)
        layout.addLayout(header_layout)

        if content:
            body = QLabel(content)
            body.setWordWrap(True)
            body.setStyleSheet("color: #94A3B8; font-size: 12px;")
            layout.addWidget(body)


class TimelineViewWidget(QWidget):
    """Stream of agent timeline activities with collapsible reasoning pane."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Reasoning pane at top
        reasoning_header = QLabel("DeepSeek-R1 Cognitive Reasoning Stream")
        reasoning_header.setStyleSheet("color: #8B5CF6; font-weight: 600; font-size: 11px;")
        main_layout.addWidget(reasoning_header)

        self.reasoning_edit = QTextEdit()
        self.reasoning_edit.setReadOnly(True)
        self.reasoning_edit.setMaximumHeight(140)
        self.reasoning_edit.setStyleSheet("background-color: #0B0E17; color: #C4B5FD; font-size: 12px;")
        main_layout.addWidget(self.reasoning_edit)

        # Timeline cards container
        timeline_header = QLabel("Execution Events & Steps")
        timeline_header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        main_layout.addWidget(timeline_header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll)

    def append_reasoning(self, text: str) -> None:
        self.reasoning_edit.insertPlainText(text)
        self.reasoning_edit.moveCursor(self.reasoning_edit.textCursor().End)

    def add_card(self, title: str, category: str, content: str) -> None:
        card = TimelineEventCard(title, category, content)
        # Insert before stretch
        count = self.cards_layout.count()
        self.cards_layout.insertWidget(count - 1, card)
        # Scroll to bottom
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def clear(self) -> None:
        self.reasoning_edit.clear()
        # Remove cards
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
