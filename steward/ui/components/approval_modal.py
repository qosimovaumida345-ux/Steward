"""
Interactive Security Approval Dialog.
Prompts developer with exact tool arguments and risk justification before privileged execution.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ApprovalModal(QDialog):
    """High-priority interactive clearance dialog."""

    decision_made = Signal(str, bool)  # (token, approved)

    def __init__(
        self,
        token: str,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.token = token
        self.setWindowTitle("Security Clearance Required")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(f"Tool Request: <font color='#F59E0B'><b>{tool_name}</b></font>")
        header.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(header)

        reason_label = QLabel(f"<b>Security Reason:</b> {reason}")
        reason_label.setWordWrap(True)
        reason_label.setStyleSheet("color: #F87171; background: #2A1215; padding: 8px; border-radius: 4px;")
        layout.addWidget(reason_label)

        args_title = QLabel("Arguments:")
        args_title.setStyleSheet("color: #94A3B8; font-weight: 500;")
        layout.addWidget(args_title)

        args_box = QTextEdit()
        args_box.setReadOnly(True)
        args_box.setPlainText(json.dumps(arguments, indent=2))
        args_box.setMaximumHeight(150)
        layout.addWidget(args_box)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reject_btn = QPushButton("Deny Action")
        reject_btn.setObjectName("dangerButton")
        reject_btn.clicked.connect(self._on_reject)
        btn_layout.addWidget(reject_btn)

        approve_btn = QPushButton("Approve Execution")
        approve_btn.setObjectName("primaryButton")
        approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(approve_btn)

        layout.addLayout(btn_layout)

    def _on_approve(self) -> None:
        self.decision_made.emit(self.token, True)
        self.accept()

    def _on_reject(self) -> None:
        self.decision_made.emit(self.token, False)
        self.reject()
