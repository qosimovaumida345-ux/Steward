"""
Status Bar Component for Steward.
Displays live daemon link status, sequence catch-up numbers, active model, and cloud replication.
"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QLabel, QStatusBar, QWidget


class AgentStatusBar(QStatusBar):
    """High-density status bar for monitoring daemon connection and metrics."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.conn_label = QLabel("DISCONNECTED")
        self.conn_label.setStyleSheet("color: #EF4444; font-weight: bold; padding: 0 4px;")

        self.model_label = QLabel("Model: deepseek-ai/deepseek-r1")
        self.model_label.setStyleSheet("color: #94A3B8; padding: 0 8px;")

        self.seq_label = QLabel("Seq: 0")
        self.seq_label.setStyleSheet("color: #94A3B8; padding: 0 8px;")

        self.sync_label = QLabel("Render Sync: Idle")
        self.sync_label.setStyleSheet("color: #10B981; padding: 0 8px;")

        self.addWidget(self.conn_label)
        self.addWidget(self.model_label)
        self.addPermanentWidget(self.seq_label)
        self.addPermanentWidget(self.sync_label)

    def set_connected(self, connected: bool) -> None:
        if connected:
            self.conn_label.setText("CONNECTED")
            self.conn_label.setStyleSheet("color: #10B981; font-weight: bold; padding: 0 4px;")
        else:
            self.conn_label.setText("DETACHED")
            self.conn_label.setStyleSheet("color: #F59E0B; font-weight: bold; padding: 0 4px;")

    def set_model(self, model_name: str) -> None:
        short_name = model_name.split("/")[-1]
        self.model_label.setText(f"Model: {short_name}")

    def set_seq(self, seq: int) -> None:
        self.seq_label.setText(f"Seq: {seq}")

    def set_sync_status(self, text: str) -> None:
        self.sync_label.setText(f"Render Sync: {text}")
