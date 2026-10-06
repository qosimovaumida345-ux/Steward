"""
Code Viewer Component for Steward Desktop UI.
Displays source code files opened from the project explorer with line numbers,
path breadcrumbs, metadata, and fast scrolling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CodeViewerWidget(QWidget):
    """Source file inspector displaying content with dark IDE typography."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.current_file_path: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header bar
        header_bar = QHBoxLayout()
        header_bar.setSpacing(6)

        self.path_label = QLabel("No file selected")
        self.path_label.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
        header_bar.addWidget(self.path_label, 1)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #64748B; font-size: 11px;")
        header_bar.addWidget(self.meta_label)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("ghostButton")
        self.copy_btn.setFixedWidth(50)
        self.copy_btn.clicked.connect(self._copy_content)
        header_bar.addWidget(self.copy_btn)

        self.reload_btn = QPushButton("↺")
        self.reload_btn.setObjectName("ghostButton")
        self.reload_btn.setFixedWidth(28)
        self.reload_btn.clicked.connect(self._reload_file)
        header_bar.addWidget(self.reload_btn)

        layout.addLayout(header_bar)

        # Monospace Code Editor
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("codeViewerEdit")
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.editor)

    def load_file(self, file_path: str) -> None:
        """Load and display the given file path."""
        self.current_file_path = file_path
        p = Path(file_path)

        if not p.is_file():
            self.path_label.setText(f"File not found: {p.name}")
            self.editor.setPlainText(f"Error: {file_path} is not an accessible file.")
            self.meta_label.setText("")
            return

        try:
            size_kb = p.stat().st_size / 1024.0
            if size_kb > 5000:
                self.editor.setPlainText(f"File is too large to preview ({size_kb:.1f} KB).")
                self.path_label.setText(p.name)
                self.meta_label.setText(f"{size_kb:.1f} KB")
                return

            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines_count = content.count("\n") + 1
            self.path_label.setText(str(p.name))
            self.path_label.setToolTip(str(p))
            self.meta_label.setText(f"{lines_count} lines | {size_kb:.1f} KB")

            self.editor.setPlainText(content)
            self.editor.moveCursor(QTextCursor.Start)

        except Exception as e:
            self.editor.setPlainText(f"Failed to read file: {e}")
            self.path_label.setText(p.name)
            self.meta_label.setText("Error")

    def _reload_file(self) -> None:
        if self.current_file_path:
            self.load_file(self.current_file_path)

    def _copy_content(self) -> None:
        from qtpy.QtWidgets import QApplication
        text = self.editor.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
