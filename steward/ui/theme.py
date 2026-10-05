"""
High-Density Dark Theme for Steward Desktop UI.
Linear / Cursor inspired aesthetic: monochrome, ultra-sharp contrast, zero emojis.
"""

from __future__ import annotations

from qtpy.QtWidgets import QApplication

DARK_STYLESHEET = """
/* Global Application Style */
QWidget {
    background-color: #090D16;
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

/* Main Window & Splitters */
QMainWindow {
    background-color: #090D16;
}

QSplitter::handle {
    background-color: #1F293D;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* Panels & Cards */
QFrame#panelFrame, QWidget#panelWidget {
    background-color: #111726;
    border: 1px solid #1F293D;
    border-radius: 4px;
}

/* Tree & List Views */
QTreeWidget, QListWidget {
    background-color: #111726;
    border: 1px solid #1F293D;
    border-radius: 4px;
    padding: 4px;
    outline: none;
}

QTreeWidget::item, QListWidget::item {
    height: 28px;
    padding: 4px 8px;
    border-radius: 2px;
}

QTreeWidget::item:hover, QListWidget::item:hover {
    background-color: #1A2333;
}

QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #1E3A8A;
    color: #FFFFFF;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0B111E;
    color: #F1F5F9;
    border: 1px solid #1F293D;
    border-radius: 4px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #2563EB;
    background-color: #0E1626;
}

/* Monospace Code Editor & Terminals */
QPlainTextEdit#terminalEdit, QTextEdit#diffViewer {
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
    background-color: #06090F;
}

/* Buttons */
QPushButton {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #273549;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #1A2333;
}

QPushButton#primaryButton {
    background-color: #2563EB;
    border: 1px solid #1D4ED8;
    color: #FFFFFF;
}

QPushButton#primaryButton:hover {
    background-color: #3B82F6;
}

QPushButton#dangerButton {
    background-color: #991B1B;
    border: 1px solid #DC2626;
    color: #FFFFFF;
}

QPushButton#dangerButton:hover {
    background-color: #B91C1C;
}

/* Combo Box Dropdown */
QComboBox {
    background-color: #111726;
    border: 1px solid #1F293D;
    border-radius: 4px;
    padding: 4px 10px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #2563EB;
}

QComboBox QAbstractItemView {
    background-color: #111726;
    border: 1px solid #1F293D;
    selection-background-color: #1E3A8A;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #090D16;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1F293D;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #334155;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #0B111E;
    border-top: 1px solid #1F293D;
    color: #64748B;
    font-size: 11px;
    padding: 2px 10px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #1F293D;
    background-color: #111726;
}

QTabBar::tab {
    background-color: #090D16;
    color: #94A3B8;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border: 1px solid transparent;
}

QTabBar::tab:selected {
    background-color: #111726;
    color: #F8FAFC;
    border-color: #1F293D #1F293D transparent #1F293D;
    font-weight: 600;
}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply the high-density dark developer stylesheet to the application."""
    app.setStyleSheet(DARK_STYLESHEET)
