"""
Entrypoint: Steward Desktop Client.
Launches the PyQt6 / QtPy high-density dark developer interface.
"""

from __future__ import annotations

import argparse
import sys

from qtpy.QtWidgets import QApplication

from steward.config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from steward.config.settings import get_settings
from steward.ui.main_window import MainWindow
from steward.ui.theme import apply_dark_theme


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Steward Desktop Client")
    parser.add_argument("--host", default=settings.daemon_host or DEFAULT_DAEMON_HOST, help="Daemon host address")
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
