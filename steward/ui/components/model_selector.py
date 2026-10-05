"""
Model Selector Dropdown Component.
Populates verified NVIDIA NIM models dynamically.
"""

from __future__ import annotations

from typing import List, Optional
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from ...brain.model_catalog import ModelCatalog


class ModelSelectorWidget(QWidget):
    """Dropdown for selecting active architectural planning or actor models."""

    model_selected = Signal(str)

    def __init__(self, catalog: Optional[ModelCatalog] = None, parent=None) -> None:
        super().__init__(parent)
        self.catalog = catalog or ModelCatalog()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("Model:")
        label.setStyleSheet("color: #94A3B8; font-weight: 500;")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.setMinimumWidth(220)
        layout.addWidget(self.combo)

        self._populate_models()
        self.combo.currentTextChanged.connect(self._on_changed)

    def _populate_models(self) -> None:
        self.combo.clear()
        profiles = self.catalog.list_all()
        for p in profiles:
            self.combo.addItem(p.display_name, p.model_id)

    def update_models(self, raw_models: List[dict]) -> None:
        self.catalog.update_from_nim_models_list(raw_models)
        self._populate_models()

    def get_selected_model_id(self) -> str:
        return self.combo.currentData() or self.combo.currentText()

    def _on_changed(self, text: str) -> None:
        mid = self.get_selected_model_id()
        if mid:
            self.model_selected.emit(mid)
