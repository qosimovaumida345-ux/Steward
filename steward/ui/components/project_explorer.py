"""
Project Explorer Component for Steward Desktop UI.
Antigravity 2.0 workspace file browser with folder navigation,
real-time file filtering, file preview events, and contextual actions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from qtpy.QtCore import QDir, QModelIndex, QSortFilterProxyModel, Qt, Signal
from qtpy.QtGui import QAction, QCursor, QIcon
from qtpy.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class FileFilterProxyModel(QSortFilterProxyModel):
    """Filter out noisy build and cache artifacts while supporting text filtering."""

    IGNORED_DIRS = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setRecursiveFilteringEnabled(True)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if not model:
            return True

        index = model.index(source_row, 0, source_parent)
        file_name = model.fileName(index)

        # Ignore hidden/build directories
        if file_name in self.IGNORED_DIRS:
            return False

        # Apply search regex/text filter if present
        pattern = self.filterRegularExpression().pattern()
        if pattern:
            return super().filterAcceptsRow(source_row, source_parent)

        return True


class ProjectExplorerWidget(QWidget):
    """
    Project workspace browser widget.
    Allows opening folders, navigating file trees, and selecting files to inspect.
    """

    file_selected = Signal(str)
    workspace_changed = Signal(str)
    reference_in_chat = Signal(str)

    def __init__(self, root_path: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self.root_path = Path(root_path or os.getcwd()).resolve()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Top Bar: Workspace folder label and actions
        header_bar = QHBoxLayout()
        header_bar.setSpacing(4)

        self.folder_label = QLabel()
        self.folder_label.setStyleSheet("font-weight: 600; color: #F1F5F9; font-size: 12px;")
        header_bar.addWidget(self.folder_label, 1)

        self.open_folder_btn = QPushButton("Open...")
        self.open_folder_btn.setObjectName("ghostButton")
        self.open_folder_btn.setToolTip("Open workspace folder")
        self.open_folder_btn.clicked.connect(self._on_choose_folder)
        header_bar.addWidget(self.open_folder_btn)

        self.refresh_btn = QPushButton("↺")
        self.refresh_btn.setObjectName("ghostButton")
        self.refresh_btn.setFixedWidth(28)
        self.refresh_btn.setToolTip("Refresh file tree")
        self.refresh_btn.clicked.connect(self._on_refresh)
        header_bar.addWidget(self.refresh_btn)

        layout.addLayout(header_bar)

        # Search / Filter Box
        self.filter_input = QLineEdit()
        self.filter_input.setObjectName("searchFilter")
        self.filter_input.setPlaceholderText("Filter files (e.g. main.py)...")
        self.filter_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_input)

        # File Tree Model & View
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(str(self.root_path))
        self.fs_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)

        self.proxy_model = FileFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.fs_model)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(16)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._on_context_menu)
        self.tree_view.clicked.connect(self._on_item_clicked)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)

        # Hide extra columns (Size, Type, Date Modified)
        for col in range(1, 4):
            self.tree_view.hideColumn(col)

        layout.addWidget(self.tree_view)

        self._update_root_path(self.root_path)

    def _update_root_path(self, path: Path) -> None:
        self.root_path = path.resolve()
        self.folder_label.setText(f"Project: {self.root_path.name}")
        self.folder_label.setToolTip(str(self.root_path))

        source_index = self.fs_model.setRootPath(str(self.root_path))
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.tree_view.setRootIndex(proxy_index)
        self.workspace_changed.emit(str(self.root_path))

    def set_workspace(self, path_str: str) -> None:
        target = Path(path_str)
        if target.is_dir():
            self._update_root_path(target)

    def get_workspace_path(self) -> str:
        return str(self.root_path)

    def _on_choose_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Select Workspace Folder",
            str(self.root_path),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )
        if chosen:
            self._update_root_path(Path(chosen))

    def _on_refresh(self) -> None:
        self.fs_model.setRootPath(str(self.root_path))
        source_index = self.fs_model.index(str(self.root_path))
        self.tree_view.setRootIndex(self.proxy_model.mapFromSource(source_index))

    def _on_filter_changed(self, text: str) -> None:
        self.proxy_model.setFilterFixedString(text.strip())

    def _get_path_from_index(self, proxy_index: QModelIndex) -> Optional[str]:
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            return None
        return self.fs_model.filePath(source_index)

    def _on_item_clicked(self, proxy_index: QModelIndex) -> None:
        file_path = self._get_path_from_index(proxy_index)
        if file_path and os.path.isfile(file_path):
            self.file_selected.emit(file_path)

    def _on_item_double_clicked(self, proxy_index: QModelIndex) -> None:
        file_path = self._get_path_from_index(proxy_index)
        if file_path and os.path.isfile(file_path):
            self.file_selected.emit(file_path)

    def _on_context_menu(self, point) -> None:
        proxy_index = self.tree_view.indexAt(point)
        if not proxy_index.isValid():
            return

        file_path = self._get_path_from_index(proxy_index)
        if not file_path:
            return

        menu = QMenu(self)

        is_file = os.path.isfile(file_path)
        if is_file:
            open_action = menu.addAction("Open in Code Viewer")
            open_action.triggered.connect(lambda: self.file_selected.emit(file_path))

            ref_action = menu.addAction("Insert @file Reference in Chat")
            rel_name = os.path.relpath(file_path, str(self.root_path))
            ref_action.triggered.connect(lambda: self.reference_in_chat.emit(f"@{rel_name}"))

            menu.addSeparator()

        copy_rel_action = menu.addAction("Copy Relative Path")
        rel_path = os.path.relpath(file_path, str(self.root_path))
        copy_rel_action.triggered.connect(lambda: self._copy_to_clipboard(rel_path))

        copy_abs_action = menu.addAction("Copy Full Path")
        copy_abs_action.triggered.connect(lambda: self._copy_to_clipboard(file_path))

        menu.addSeparator()
        reveal_action = menu.addAction("Reveal in File Explorer")
        reveal_action.triggered.connect(lambda: self._reveal_in_explorer(file_path))

        menu.exec_(QCursor.pos())

    def _copy_to_clipboard(self, text: str) -> None:
        from qtpy.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _reveal_in_explorer(self, target_path: str) -> None:
        import subprocess
        norm_path = os.path.normpath(target_path)
        if os.name == "nt":
            if os.path.isfile(norm_path):
                subprocess.Popen(["explorer", "/select,", norm_path])
            else:
                subprocess.Popen(["explorer", norm_path])
        elif os.name == "posix":
            subprocess.Popen(["xdg-open", os.path.dirname(norm_path)])
