"""
Terminal Output Widget Component.
Displays real-time VT100 / command output with autoscroll and monospace typography.
"""

from __future__ import annotations

import re
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class TerminalWidget(QWidget):
    """Real-time console output view."""

    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel("Terminal Console Output")
        header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        layout.addWidget(header)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("terminalEdit")
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.editor)

    def append_output(self, text: str) -> None:
        clean = self.ANSI_ESCAPE.sub("", text)
        self.editor.moveCursor(QTextCursor.End)
        self.editor.insertPlainText(clean + "\n")
        self.editor.moveCursor(QTextCursor.End)

    def clear(self) -> None:
        self.editor.clear()
