"""
Tests for Antigravity 2.0 UI Components:
Project Explorer, Code Viewer, Chat View, Chat Composer, Session List, and MainWindow layout.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

from steward.ui.components.chat_composer import ChatComposerWidget
from steward.ui.components.chat_view import ChatViewWidget
from steward.ui.components.code_viewer import CodeViewerWidget
from steward.ui.components.diff_viewer import DiffViewerWidget
from steward.ui.components.project_explorer import ProjectExplorerWidget
from steward.ui.components.session_list import SessionListWidget
from steward.ui.components.terminal_widget import TerminalWidget
from steward.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for Qt widget testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_project_explorer_widget(qapp, tmp_path):
    # Create test directory structure
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()
    test_file = sub_dir / "app.py"
    test_file.write_text("print('hello')", encoding="utf-8")

    explorer = ProjectExplorerWidget(root_path=str(tmp_path))
    assert Path(explorer.get_workspace_path()) == tmp_path.resolve()

    selected_files = []
    explorer.file_selected.connect(lambda p: selected_files.append(p))

    # Test setting workspace
    explorer.set_workspace(str(sub_dir))
    assert Path(explorer.get_workspace_path()) == sub_dir.resolve()


def test_code_viewer_widget(qapp, tmp_path):
    viewer = CodeViewerWidget()
    test_file = tmp_path / "example.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n", encoding="utf-8")

    viewer.load_file(str(test_file))
    assert "Line 1" in viewer.editor.toPlainText()
    assert "example.txt" in viewer.path_label.text()
    assert "lines" in viewer.meta_label.text()

    # Non-existent file
    viewer.load_file(str(tmp_path / "missing.txt"))
    assert "File not found" in viewer.path_label.text()


def test_chat_view_widget(qapp):
    chat = ChatViewWidget()
    chat.show()
    assert not chat.welcome_widget.isHidden()

    # User message
    chat.add_user_message("Test user prompt")
    assert chat.welcome_widget.isHidden()

    # Agent response and thinking
    agent_card = chat.start_agent_response("DeepSeek-V4.1 Flash")
    assert agent_card is not None
    chat.append_reasoning("Analyzing step 1...")
    assert "Analyzing step 1..." in agent_card.thinking_block.content_edit.toPlainText()

    # Plan
    chat.add_plan("Refactor test", [
        {"step_id": 1, "title": "Check code", "status": "in_progress"},
        {"step_id": 2, "title": "Run pytest", "status": "pending"},
    ])
    assert agent_card.plan_card is not None

    # Tool execution
    chat.add_tool_execution("run_command", "pytest tests/", output="40 passed", status="success")

    # Clear
    chat.clear()
    assert not chat.welcome_widget.isHidden()
    chat.close()


def test_chat_composer_widget(qapp):
    composer = ChatComposerWidget()
    dispatched = []
    composer.dispatch_requested.connect(lambda text, model: dispatched.append((text, model)))

    composer.editor.setPlainText("Hello agent")
    composer._on_dispatch()
    assert len(dispatched) == 1
    assert dispatched[0][0] == "Hello agent"
    assert composer.editor.toPlainText() == ""

    # Running toggle
    composer.set_running(True)
    assert composer.cancel_btn.isEnabled()
    assert not composer.send_btn.isEnabled()

    composer.set_running(False)
    assert not composer.cancel_btn.isEnabled()
    assert composer.send_btn.isEnabled()


def test_session_list_widget(qapp):
    slist = SessionListWidget()
    selected = []
    slist.session_selected.connect(lambda sid: selected.append(sid))

    sessions = [
        {"session_id": "sess-001", "title": "Task One", "status": "COMPLETED"},
        {"session_id": "sess-002", "title": "Task Two", "status": "RUNNING"},
    ]
    slist.update_sessions(sessions)
    assert slist.session_tree.topLevelItemCount() == 2

    # Filter
    slist.search_input.setText("Two")
    assert slist.session_tree.topLevelItemCount() == 1


def test_main_window_structure(qapp, tmp_path):
    window = MainWindow(host="127.0.0.1", port=8765, workspace_dir=str(tmp_path))
    window.show()
    assert window.project_explorer is not None
    assert window.chat_view is not None
    assert window.chat_composer is not None
    assert window.code_viewer is not None
    assert window.diff_viewer is not None
    assert window.terminal_widget is not None
    assert window.status_bar is not None

    # Test toggles
    initial_sidebar_hidden = window.sidebar_tabs.isHidden()
    window._toggle_sidebar()
    assert window.sidebar_tabs.isHidden() != initial_sidebar_hidden
    window._toggle_sidebar()

    if hasattr(window, "_refresh_timer") and window._refresh_timer.isActive():
        window._refresh_timer.stop()
    window.worker.stop()
    window.close()
