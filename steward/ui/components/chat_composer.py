"""
Chat Composer Component for Steward Desktop UI.
Antigravity 2.0 / Cursor IDE inspired multi-line prompt input:
- Auto-growing multi-line text input
- Enter to dispatch / Shift+Enter for newline
- Integrated model selector dropdown
- Action toolbar with cancel and send triggers
"""

from __future__ import annotations

from typing import Optional

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .model_selector import ModelSelectorWidget


class PromptInputEdit(QPlainTextEdit):
    """Multi-line text editor intercepting Enter key for dispatch."""

    enter_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                # Insert newline
                super().keyPressEvent(event)
            else:
                # Dispatch
                event.accept()
                self.enter_pressed.emit()
                return
        else:
            super().keyPressEvent(event)


class ChatComposerWidget(QWidget):
    """Modern bottom composer bar for chatting and dispatching tasks."""

    dispatch_requested = Signal(str, str)
    cancel_requested = Signal()
    folder_pick_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        container = QFrame(self)
        container.setObjectName("panelFrame")
        container.setStyleSheet(
            "QFrame#panelFrame { background-color: #0E1524; border: 1px solid #1E293B; "
            "border-radius: 8px; padding: 4px; }"
        )

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(container)

        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(8, 8, 8, 8)
        inner_layout.setSpacing(8)

        # Multi-line Prompt Editor
        self.editor = PromptInputEdit()
        self.editor.setPlaceholderText(
            "Message Steward or dispatch autonomous engineering task... "
            "(Press Enter to send, Shift+Enter for newline)"
        )
        self.editor.setMinimumHeight(65)
        self.editor.setMaximumHeight(160)
        self.editor.setStyleSheet(
            "QPlainTextEdit { background-color: transparent; border: none; color: #F8FAFC; "
            "font-size: 13px; line-height: 1.4; padding: 2px; } "
            "QPlainTextEdit:focus { border: none; background-color: transparent; }"
        )
        self.editor.enter_pressed.connect(self._on_dispatch)
        self.editor.textChanged.connect(self._on_text_changed)
        inner_layout.addWidget(self.editor)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        # Left: Model selector & quick tools
        self.model_selector = ModelSelectorWidget()
        action_bar.addWidget(self.model_selector)

        action_bar.addStretch()

        # Right: Character count & actions
        self.char_label = QLabel("0 chars")
        self.char_label.setStyleSheet("color: #64748B; font-size: 11px;")
        action_bar.addWidget(self.char_label)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setToolTip("Cancel ongoing task execution")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_btn.setEnabled(False)
        action_bar.addWidget(self.cancel_btn)

        self.send_btn = QPushButton("Send  ↵")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.setToolTip("Dispatch task to autonomous agent (Enter)")
        self.send_btn.clicked.connect(self._on_dispatch)
        action_bar.addWidget(self.send_btn)

        inner_layout.addLayout(action_bar)

    def _on_text_changed(self) -> None:
        chars = len(self.editor.toPlainText())
        self.char_label.setText(f"{chars} chars")

    def _on_dispatch(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        selected_model = self.model_selector.get_selected_model_id()
        self.editor.clear()
        self.dispatch_requested.emit(text, selected_model)

    def insert_text(self, text: str) -> None:
        current = self.editor.toPlainText()
        if current and not current.endswith(" "):
            self.editor.insertPlainText(" " + text)
        else:
            self.editor.insertPlainText(text)
        self.editor.setFocus()

    def set_running(self, running: bool) -> None:
        self.cancel_btn.setEnabled(running)
        self.send_btn.setEnabled(not running)
