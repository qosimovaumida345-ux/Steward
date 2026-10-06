"""
Diff Viewer Component.
Displays colorized unified git-style code diffs for agent file modifications.
"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QTextCharFormat, QTextCursor
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DiffViewerWidget(QWidget):
    """High-contrast syntax-colored diff viewer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_diff = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header_bar = QHBoxLayout()
        header_bar.setSpacing(6)

        header = QLabel("File Changes & Unified Diffs")
        header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        header_bar.addWidget(header, 1)

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("ghostButton")
        copy_btn.setFixedWidth(50)
        copy_btn.clicked.connect(self._copy_diff)
        header_bar.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("ghostButton")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(lambda: self.set_diff(""))
        header_bar.addWidget(clear_btn)

        layout.addLayout(header_bar)

        self.editor = QTextEdit()
        self.editor.setObjectName("diffViewer")
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.editor)

    def set_diff(self, diff_text: str) -> None:
        """Render diff text with syntax coloring."""
        self._current_diff = diff_text
        self.editor.clear()
        if not diff_text:
            self.editor.setPlainText("(No file changes recorded)")
            return

        cursor = self.editor.textCursor()

        default_fmt = QTextCharFormat()
        default_fmt.setForeground(QColor("#94A3B8"))

        add_fmt = QTextCharFormat()
        add_fmt.setForeground(QColor("#34D399"))
        add_fmt.setBackground(QColor("#064E3B"))

        del_fmt = QTextCharFormat()
        del_fmt.setForeground(QColor("#F87171"))
        del_fmt.setBackground(QColor("#450A0A"))

        chunk_fmt = QTextCharFormat()
        chunk_fmt.setForeground(QColor("#38BDF8"))

        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                cursor.insertText(line + "\n", add_fmt)
            elif line.startswith("-") and not line.startswith("---"):
                cursor.insertText(line + "\n", del_fmt)
            elif line.startswith("@@"):
                cursor.insertText(line + "\n", chunk_fmt)
            else:
                cursor.insertText(line + "\n", default_fmt)

        self.editor.moveCursor(QTextCursor.Start)

    def _copy_diff(self) -> None:
        if self._current_diff:
            QApplication.clipboard().setText(self._current_diff)
