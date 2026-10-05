"""
Entrypoint: Steward Desktop Client.
Launches the PyQt6 / QtPy high-density dark developer interface.
Supports live connection to Render Cloud Daemon or local instance.
"""

from __future__ import annotations

import argparse
import ctypes
from pathlib import Path
import sys
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
    main()
