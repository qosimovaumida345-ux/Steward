"""
Terminal Output Widget Component.
Displays real-time VT100 / command output with autoscroll and monospace typography.
"""

from __future__ import annotations

import re
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TerminalWidget(QWidget):
    """Real-time console output view."""

    ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header_bar = QHBoxLayout()
        header_bar.setSpacing(6)

        header = QLabel("Terminal Console Output")
        header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        header_bar.addWidget(header, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("ghostButton")
        copy_btn.setFixedWidth(50)
        copy_btn.clicked.connect(self._copy_output)
        header_bar.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("ghostButton")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(self.clear)
        header_bar.addWidget(clear_btn)

        layout.addLayout(header_bar)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("terminalEdit")
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.editor)

    def append_output(self, text: str) -> None:
        clean = self.ANSI_ESCAPE.sub("", text)
        self.editor.moveCursor(QTextCursor.End)
        self.editor.insertPlainText(clean)
        self.editor.moveCursor(QTextCursor.End)

    def clear(self) -> None:
        self.editor.clear()

    def _copy_output(self) -> None:
        text = self.editor.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
