"""
Conversational Chat Interface Component for Steward Desktop UI.
Antigravity 2.0 / Cursor IDE inspired chat stream:
- Conversational user bubbles
- Collapsible DeepSeek CoT reasoning stream
- Interactive plan cards with step DAG progress
- Tool invocation cards with command & output disclosures
- Formatted markdown / code snippet blocks
"""

from __future__ import annotations

import html
import re
import time
from typing import Any, Dict, List, Optional

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor, QTextCursor
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class UserMessageCard(QFrame):
    """Modern dark user chat message bubble."""

    def __init__(self, text: str, timestamp: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("userMessageBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: Avatar + Timestamp
        header = QHBoxLayout()
        header.setSpacing(8)

        avatar = QLabel("YOU")
        avatar.setStyleSheet(
            "background-color: #3B82F6; color: #FFFFFF; font-weight: 700; "
            "font-size: 10px; padding: 2px 8px; border-radius: 4px;"
        )
        header.addWidget(avatar)

        ts_text = timestamp or time.strftime("%H:%M:%S")
        time_label = QLabel(ts_text)
        time_label.setStyleSheet("color: #64748B; font-size: 11px;")
        header.addWidget(time_label)

        header.addStretch()
        layout.addLayout(header)

        # Body
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("color: #F8FAFC; font-size: 13px; line-height: 1.4;")
        layout.addWidget(body)


class CollapsibleThinkingBlock(QFrame):
    """Collapsible card displaying DeepSeek-R1 / NIM reasoning CoT stream."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("thinkingCard")
        self._is_collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(6)

        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setObjectName("ghostButton")
        self.toggle_btn.setFixedSize(22, 22)
        self.toggle_btn.clicked.connect(self.toggle)
        header.addWidget(self.toggle_btn)

        self.title_label = QLabel("Thinking Process (DeepSeek CoT)")
        self.title_label.setStyleSheet("color: #A78BFA; font-weight: 600; font-size: 11px;")
        header.addWidget(self.title_label)

        self.status_badge = QLabel("Streaming...")
        self.status_badge.setStyleSheet(
            "color: #C4B5FD; background: #2E1065; font-size: 10px; font-weight: bold; "
            "padding: 1px 6px; border-radius: 3px;"
        )
        header.addWidget(self.status_badge)

        header.addStretch()
        layout.addLayout(header)

        self.content_edit = QPlainTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setMaximumHeight(140)
        self.content_edit.setStyleSheet(
            "background-color: #080C16; color: #C4B5FD; font-family: 'Cascadia Code', Consolas, monospace; "
            "font-size: 11px; border: 1px solid #2E1065; border-radius: 4px; padding: 4px;"
        )
        layout.addWidget(self.content_edit)

    def append_chunk(self, chunk: str) -> None:
        self.content_edit.moveCursor(QTextCursor.End)
        self.content_edit.insertPlainText(chunk)
        self.content_edit.moveCursor(QTextCursor.End)

    def finish_thinking(self) -> None:
        self.status_badge.setText("Completed")
        self.status_badge.setStyleSheet(
            "color: #10B981; background: #064E3B; font-size: 10px; font-weight: bold; "
            "padding: 1px 6px; border-radius: 3px;"
        )

    def toggle(self) -> None:
        self._is_collapsed = not self._is_collapsed
        if self._is_collapsed:
            self.content_edit.hide()
            self.toggle_btn.setText("▶")
        else:
            self.content_edit.show()
            self.toggle_btn.setText("▼")


class PlanCard(QFrame):
    """Structured plan card showing goal and step DAG."""

    def __init__(self, goal: str, steps: List[Dict[str, Any]], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("planCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        badge = QLabel("EXECUTION PLAN")
        badge.setStyleSheet(
            "background-color: #065F46; color: #34D399; font-weight: 700; "
            "font-size: 10px; padding: 2px 8px; border-radius: 3px;"
        )
        header.addWidget(badge)

        goal_lbl = QLabel(goal)
        goal_lbl.setStyleSheet("color: #F1F5F9; font-weight: 600; font-size: 12px;")
        header.addWidget(goal_lbl, 1)
        layout.addLayout(header)

        self.steps_container = QVBoxLayout()
        self.steps_container.setSpacing(4)
        self.step_labels: Dict[int, QLabel] = {}

        for step in steps:
            sid = step.get("step_id", 0)
            title = step.get("title", "")
            status = step.get("status", "pending")

            lbl = QLabel(self._format_step_text(sid, title, status))
            lbl.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 2px 4px;")
            self.steps_container.addWidget(lbl)
            self.step_labels[sid] = lbl

        layout.addLayout(self.steps_container)

    def _format_step_text(self, sid: int, title: str, status: str) -> str:
        icon = "✓" if status == "completed" else "▶" if status == "in_progress" else "○"
        return f"  {icon}  Step {sid}: {title}"

    def update_step_status(self, sid: int, title: str, status: str) -> None:
        if sid in self.step_labels:
            self.step_labels[sid].setText(self._format_step_text(sid, title, status))
            color = "#34D399" if status == "completed" else "#60A5FA" if status == "in_progress" else "#94A3B8"
            self.step_labels[sid].setStyleSheet(f"color: {color}; font-size: 12px; padding: 2px 4px;")


class ToolExecutionCard(QFrame):
    """Card representing a tool invocation (command, edit, surfer) with output toggle."""

    def __init__(self, tool_name: str, details: str, output: str = "", status: str = "success", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toolExecutionCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)

        badge = QLabel(f"⚡ {tool_name}")
        badge.setStyleSheet(
            "background-color: #1E3A8A; color: #93C5FD; font-weight: 700; "
            "font-size: 10px; padding: 2px 6px; border-radius: 3px;"
        )
        header.addWidget(badge)

        desc = QLabel(details)
        desc.setStyleSheet("color: #E2E8F0; font-family: 'Cascadia Code', monospace; font-size: 12px;")
        desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.addWidget(desc, 1)

        status_lbl = QLabel(status.upper())
        status_color = "#34D399" if status == "success" else "#F87171" if status == "error" else "#60A5FA"
        status_lbl.setStyleSheet(f"color: {status_color}; font-size: 10px; font-weight: bold;")
        header.addWidget(status_lbl)

        layout.addLayout(header)

        if output.strip():
            self.output_edit = QPlainTextEdit()
            self.output_edit.setReadOnly(True)
            self.output_edit.setPlainText(output.strip()[:4000])
            self.output_edit.setMaximumHeight(90)
            self.output_edit.setStyleSheet(
                "background-color: #06090F; color: #94A3B8; font-family: 'Cascadia Code', monospace; "
                "font-size: 11px; border: 1px solid #1E293B; border-radius: 4px;"
            )
            layout.addWidget(self.output_edit)


class AgentMessageCard(QFrame):
    """Comprehensive agent response block container."""

    def __init__(self, model_name: str = "DeepSeek-V4.1 Flash", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("agentMessageContainer")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(8)

        # Header: Avatar + Model + Status
        header = QHBoxLayout()
        header.setSpacing(8)

        avatar = QLabel("STEWARD")
        avatar.setStyleSheet(
            "background-color: #6366F1; color: #FFFFFF; font-weight: 700; "
            "font-size: 10px; padding: 2px 8px; border-radius: 4px;"
        )
        header.addWidget(avatar)

        self.model_badge = QLabel(model_name)
        self.model_badge.setStyleSheet(
            "color: #94A3B8; background: #1E293B; font-size: 10px; font-weight: 500; "
            "padding: 2px 6px; border-radius: 3px;"
        )
        header.addWidget(self.model_badge)

        self.status_pill = QLabel("Thinking...")
        self.status_pill.setStyleSheet("color: #60A5FA; font-size: 11px; font-weight: 600;")
        header.addWidget(self.status_pill)

        header.addStretch()
        self.layout.addLayout(header)

        # Thinking block
        self.thinking_block = CollapsibleThinkingBlock()
        self.layout.addWidget(self.thinking_block)

        # Dynamic inner widgets (plans, tools, content)
        self.content_label: Optional[QLabel] = None
        self.plan_card: Optional[PlanCard] = None

    def append_thinking(self, chunk: str) -> None:
        self.thinking_block.append_chunk(chunk)

    def finish_thinking(self) -> None:
        self.thinking_block.finish_thinking()
        self.status_pill.setText("Executing")
        self.status_pill.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 600;")

    def add_plan(self, goal: str, steps: List[Dict[str, Any]]) -> None:
        self.plan_card = PlanCard(goal, steps)
        self.layout.addWidget(self.plan_card)

    def add_tool_call(self, tool_name: str, details: str, output: str = "", status: str = "success") -> None:
        card = ToolExecutionCard(tool_name, details, output, status)
        self.layout.addWidget(card)

    def set_content(self, text: str) -> None:
        if not self.content_label:
            self.content_label = QLabel()
            self.content_label.setWordWrap(True)
            self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.content_label.setStyleSheet("color: #E2E8F0; font-size: 13px; line-height: 1.5;")
            self.layout.addWidget(self.content_label)
        self.content_label.setText(text)

    def set_status(self, status_text: str, color: str = "#10B981") -> None:
        self.status_pill.setText(status_text)
        self.status_pill.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")


class ChatViewWidget(QWidget):
    """
    Antigravity 2.0 Conversational Chat Stream.
    Handles message cards, thinking disclosures, plan progress, and welcome suggestions.
    """

    prompt_suggested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(10, 6, 10, 6)
        header_bar.setSpacing(8)

        self.chat_title = QLabel("Chat Stream")
        self.chat_title.setStyleSheet("color: #F1F5F9; font-weight: 700; font-size: 13px;")
        header_bar.addWidget(self.chat_title)

        self.session_badge = QLabel("No Active Session")
        self.session_badge.setStyleSheet(
            "background-color: #1E293B; color: #94A3B8; font-size: 11px; "
            "padding: 2px 8px; border-radius: 4px;"
        )
        header_bar.addWidget(self.session_badge)

        header_bar.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("ghostButton")
        self.clear_btn.setToolTip("Clear messages from view")
        self.clear_btn.clicked.connect(self.clear)
        header_bar.addWidget(self.clear_btn)

        main_layout.addLayout(header_bar)

        # Scroll Area for Messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(12)

        self.welcome_widget = self._build_welcome_widget()
        self.messages_layout.addWidget(self.welcome_widget)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area)

        self.current_agent_card: Optional[AgentMessageCard] = None

    def _build_welcome_widget(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("surfaceCard")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("STEWARD 2.0")
        logo.setStyleSheet("font-size: 22px; font-weight: 900; letter-spacing: 2px; color: #60A5FA;")
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        subtitle = QLabel("Autonomous Developer Agent — Powered by DeepSeek & NVIDIA NIM")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Suggestions Grid
        suggestions_box = QVBoxLayout()
        suggestions_box.setSpacing(8)

        prompts = [
            ("⚡ Audit Codebase & Verify Tests", "Run full pytest suite and report any coverage or stability issues."),
            ("🔍 Architecture Scan", "Analyze project structure, dependencies, and daemon endpoints."),
            ("🛠️ Autonomous Refactor", "Refactor storage synchronization and add end-to-end integration tests."),
        ]

        for title, p_text in prompts:
            btn = QPushButton(f"{title}\n{p_text}")
            btn.setObjectName("ghostButton")
            btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 10px 14px; border: 1px solid #1E293B; "
                "border-radius: 6px; background: #0E1524; color: #CBD5E1; } "
                "QPushButton:hover { background: #162033; border-color: #3B82F6; color: #FFFFFF; }"
            )
            btn.clicked.connect(lambda _, text=p_text: self.prompt_suggested.emit(text))
            suggestions_box.addWidget(btn)

        layout.addLayout(suggestions_box)
        return widget

    def set_session_info(self, session_id: str, title: Optional[str] = None) -> None:
        t = title or session_id
        self.chat_title.setText(f"Session: {t[:35]}")
        self.session_badge.setText(f"ID: {session_id[:10]}")

    def add_user_message(self, text: str) -> None:
        self.welcome_widget.hide()
        card = UserMessageCard(text)
        self._insert_card(card)

    def start_agent_response(self, model_name: str = "DeepSeek-V4.1 Flash") -> AgentMessageCard:
        self.welcome_widget.hide()
        card = AgentMessageCard(model_name)
        self.current_agent_card = card
        self._insert_card(card)
        return card

    def append_reasoning(self, chunk: str) -> None:
        if not self.current_agent_card:
            self.start_agent_response()
        if self.current_agent_card:
            self.current_agent_card.append_thinking(chunk)
            self._scroll_to_bottom()

    def add_plan(self, goal: str, steps: List[Dict[str, Any]]) -> None:
        if not self.current_agent_card:
            self.start_agent_response()
        if self.current_agent_card:
            self.current_agent_card.finish_thinking()
            self.current_agent_card.add_plan(goal, steps)
            self._scroll_to_bottom()

    def add_tool_execution(self, tool_name: str, details: str, output: str = "", status: str = "success") -> None:
        if not self.current_agent_card:
            self.start_agent_response()
        if self.current_agent_card:
            self.current_agent_card.add_tool_call(tool_name, details, output, status)
            self._scroll_to_bottom()

    def finish_agent_response(self, summary: str = "Completed successfully") -> None:
        if self.current_agent_card:
            self.current_agent_card.set_status(summary, color="#10B981")
            self.current_agent_card = None

    def _insert_card(self, widget: QWidget) -> None:
        # Insert before bottom stretch
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear(self) -> None:
        self.current_agent_card = None
        # Remove all widgets except welcome and stretch
        while self.messages_layout.count() > 2:
            item = self.messages_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.welcome_widget.show()
