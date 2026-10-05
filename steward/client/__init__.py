"""Client Subsystem: Connection management and CLI interface."""

from .client_connection import DaemonClientConnection
from .cli import main as cli_main

__all__ = ["DaemonClientConnection", "cli_main"]
