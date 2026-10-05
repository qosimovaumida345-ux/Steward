"""
Diff Viewer Component.
Displays colorized unified git-style code diffs for agent file modifications.
"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QTextCharFormat, QTextCursor
from qtpy.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class DiffViewerWidget(QWidget):
    """High-contrast syntax-colored diff viewer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel("File Changes & Unified Diffs")
        header.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px;")
        layout.addWidget(header)

        self.editor = QTextEdit()
        self.editor.setObjectName("diffViewer")
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.editor)

    def set_diff(self, diff_text: str) -> None:
        """Render diff text with syntax coloring."""
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
