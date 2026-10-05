"""
Entrypoint: Headless Cloud Daemon Service.
Runs the background autonomous agent daemon on Windows or Linux servers.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from steward.config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from steward.config.settings import get_settings
from steward.daemon.server import run_daemon_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def main() -> None:
    settings = get_settings()
    env_port = int(os.environ["PORT"]) if "PORT" in os.environ else None

    parser = argparse.ArgumentParser(description="Steward Headless Cloud Daemon")
    parser.add_argument("--host", default=settings.daemon_host or DEFAULT_DAEMON_HOST, help="Daemon host address")
    parser.add_argument("--port", type=int, default=env_port or settings.daemon_port or DEFAULT_DAEMON_PORT, help="Daemon port")
    args = parser.parse_args()

    host = args.host
    port = args.port

    print("==================================================")
    print("  STEWARD HEADLESS CLOUD DAEMON")
    print(f"  Listening on: http://{host}:{port}")
    print(f"  SQLite Store: {settings.sqlite_path}")
    print(f"  Render Sync:  {'Enabled' if settings.render_sync_enabled and settings.render_postgres_dsn else 'Disabled/Local'}")
    print("==================================================")

    run_daemon_server(host=host, port=port)


if __name__ == "__main__":
    main()
