"""
Entrypoint: Steward Desktop Client.
Launches the PyQt6 / QtPy high-density dark developer interface.
Supports live connection to Render Cloud Daemon or local instance.
"""

from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import sys
import threading
import traceback

from qtpy.QtWidgets import QApplication

from steward.config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT, DEFAULT_SERVER_URL
from steward.config.settings import get_settings
from steward.ui.main_window import MainWindow
from steward.ui.theme import apply_dark_theme


def setup_crash_handler() -> Path:
    crash_dir = Path.home() / ".steward"
    crash_dir.mkdir(parents=True, exist_ok=True)
    crash_log = crash_dir / "steward_app_crash.log"

    # Ensure stdout/stderr are not None in windowed PyInstaller mode
    if sys.stdout is None:
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
    if sys.stderr is None:
        try:
            sys.stderr = open(crash_log, "a", encoding="utf-8")
        except Exception:
            pass

    # Ensure Qt plugin path includes bundled platforms plugins if frozen
    if hasattr(sys, "_MEIPASS"):
        meipass_path = Path(sys._MEIPASS)
        qt_plugins = meipass_path / "PyQt6" / "Qt6" / "plugins"
        if qt_plugins.is_dir():
            os.environ["QT_PLUGIN_PATH"] = str(qt_plugins)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash Report ---\n{err_text}\n")
        except Exception:
            pass

        try:
            with open("steward_app_crash.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash Report ---\n{err_text}\n")
        except Exception:
            pass

        # Visual feedback on Windows
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Steward App encountered an unexpected error:\n\n{exc_value}\n\nDetails saved to:\n{crash_log}",
                "Steward Error",
                0x10 | 0x0,  # MB_ICONERROR | MB_OK
            )
        except Exception:
            pass

        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception

    def handle_thread_exception(args):
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        handle_exception(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = handle_thread_exception

    return crash_log


def main() -> None:
    setup_crash_handler()
    settings = get_settings()

    default_host = settings.server_url or settings.daemon_host or DEFAULT_SERVER_URL

    parser = argparse.ArgumentParser(description="Steward Desktop Client")
    parser.add_argument("--host", default=default_host, help="Daemon or server URL/host address")
    parser.add_argument("--port", type=int, default=settings.daemon_port or DEFAULT_DAEMON_PORT, help="Daemon port")
    args = parser.parse_args()

    host = args.host
    port = args.port

    app = QApplication(sys.argv)
    apply_dark_theme(app)

    window = MainWindow(host=host, port=port)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        crash_log = Path.home() / ".steward" / "steward_app_crash.log"
        err_msg = traceback.format_exc()
        try:
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n--- Fatal Startup Exception ---\n{err_msg}\n")
        except Exception:
            pass
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Failed to launch Steward Desktop Client:\n\n{e}\n\nSee log for details:\n{crash_log}",
                "Steward Startup Error",
                0x10 | 0x0,
            )
        except Exception:
            pass
        sys.exit(1)
