"""
Antigravity 2.0 / Cursor Inspired Modern Dark Theme for Steward Desktop UI.
High-density obsidian dark palette, sharp electric blue and indigo accents,
custom scrollbars, sleek card frames, and modern developer typography.
"""

from __future__ import annotations

from qtpy.QtWidgets import QApplication

DARK_STYLESHEET = """
/* ==========================================================================
   Global Application Styles & Typography
   ========================================================================== */
QWidget {
    background-color: #0A0E17;
    color: #E2E8F0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QMainWindow {
    background-color: #0A0E17;
}

/* ==========================================================================
   Splitters & Dividers
   ========================================================================== */
QSplitter::handle {
    background-color: #161F30;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #3B82F6;
}

/* ==========================================================================
   Panels, Frames & Cards
   ========================================================================== */
QFrame#panelFrame, QWidget#panelWidget {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 6px;
}

QFrame#surfaceCard {
    background-color: #131C2E;
    border: 1px solid #1E293B;
    border-radius: 8px;
}

/* Chat Message Bubbles */
QFrame#userMessageBubble {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 14px;
}

QFrame#agentMessageContainer {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 10px;
    padding: 12px 16px;
}

QFrame#thinkingCard {
    background-color: #0D1220;
    border: 1px solid #2E1065;
    border-radius: 6px;
    padding: 8px 12px;
}

QFrame#toolExecutionCard {
    background-color: #0B111E;
    border: 1px solid #1E293B;
    border-left: 3px solid #3B82F6;
    border-radius: 6px;
    padding: 8px 12px;
}

QFrame#planCard {
    background-color: #0B111E;
    border: 1px solid #1E293B;
    border-left: 3px solid #10B981;
    border-radius: 6px;
    padding: 10px 14px;
}

/* ==========================================================================
   Tree Views, List Views & Project Explorer
   ========================================================================== */
QTreeView, QTreeWidget, QListWidget {
    background-color: #0C111C;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    font-size: 13px;
    color: #CBD5E1;
}

QTreeView::item, QTreeWidget::item, QListWidget::item {
    height: 30px;
    padding: 2px 6px;
    border-radius: 4px;
}

QTreeView::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #172237;
    color: #F8FAFC;
}

QTreeView::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #1E3A8A;
    color: #FFFFFF;
}

QTreeView::branch {
    background-color: transparent;
}

QHeaderView::section {
    background-color: #0C111C;
    color: #94A3B8;
    border: none;
    border-bottom: 1px solid #1E293B;
    padding: 4px 8px;
    font-weight: 600;
    font-size: 11px;
}

/* ==========================================================================
   Input Fields & Editors
   ========================================================================== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0B101D;
    color: #F8FAFC;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #0D1527;
}

QLineEdit#searchFilter {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}

QLineEdit#searchFilter:focus {
    border-color: #3B82F6;
}

/* Monospace Code Editor & Terminals */
QPlainTextEdit#terminalEdit, QTextEdit#diffViewer, QPlainTextEdit#codeViewerEdit {
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    background-color: #050810;
    color: #E2E8F0;
    border: 1px solid #1E293B;
    border-radius: 6px;
}

/* ==========================================================================
   Buttons
   ========================================================================== */
QPushButton {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #2E3E56;
    border-color: #475569;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #162032;
}

QPushButton:disabled {
    background-color: #0F172A;
    border-color: #1E293B;
    color: #475569;
}

/* Primary Button (Electric Blue) */
QPushButton#primaryButton {
    background-color: #2563EB;
    border: 1px solid #1D4ED8;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #3B82F6;
    border-color: #2563EB;
}

QPushButton#primaryButton:pressed {
    background-color: #1D4ED8;
}

/* Secondary Ghost Button */
QPushButton#ghostButton {
    background-color: transparent;
    border: 1px solid #1E293B;
    color: #94A3B8;
}

QPushButton#ghostButton:hover {
    background-color: #172237;
    border-color: #334155;
    color: #F8FAFC;
}

/* Danger Button */
QPushButton#dangerButton {
    background-color: #991B1B;
    border: 1px solid #DC2626;
    color: #FFFFFF;
    font-weight: 600;
}

QPushButton#dangerButton:hover {
    background-color: #B91C1C;
}

QPushButton#dangerButton:pressed {
    background-color: #7F1D1D;
}

/* ==========================================================================
   Dropdowns & Combo Boxes
   ========================================================================== */
QComboBox {
    background-color: #0F172A;
    color: #F1F5F9;
    border: 1px solid #1E293B;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #3B82F6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #0F172A;
    color: #F1F5F9;
    border: 1px solid #334155;
    border-radius: 6px;
    selection-background-color: #1E3A8A;
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}

/* ==========================================================================
   Tab Widgets (IDE Style)
   ========================================================================== */
QTabWidget::pane {
    border: 1px solid #1E293B;
    background-color: #0B101D;
    border-radius: 0 0 6px 6px;
}

QTabBar::tab {
    background-color: #080C14;
    color: #94A3B8;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-size: 12px;
    font-weight: 500;
}

QTabBar::tab:hover {
    color: #E2E8F0;
    background-color: #0F172A;
}

QTabBar::tab:selected {
    background-color: #0B101D;
    color: #60A5FA;
    border-top: 1px solid #1E293B;
    border-left: 1px solid #1E293B;
    border-right: 1px solid #1E293B;
    border-bottom: 2px solid #3B82F6;
    font-weight: 600;
}

/* ==========================================================================
   Scrollbars (Minimalist Modern)
   ========================================================================== */
QScrollBar:vertical {
    border: none;
    background: #080C14;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #1E293B;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3B82F6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    border: none;
    background: none;
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #080C14;
    height: 6px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #1E293B;
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #3B82F6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    border: none;
    background: none;
    width: 0px;
}

/* ==========================================================================
   Scroll Area
   ========================================================================== */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* ==========================================================================
   Status Bar
   ========================================================================== */
QStatusBar {
    background-color: #060910;
    border-top: 1px solid #161F30;
    color: #64748B;
    font-size: 11px;
    padding: 3px 12px;
}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply the Antigravity 2.0 obsidian dark developer stylesheet to the application."""
    app.setStyleSheet(DARK_STYLESHEET)
