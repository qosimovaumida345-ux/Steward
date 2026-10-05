"""
CLI Interface for Steward Daemon Management.
"""

from __future__ import annotations

import argparse
import json
import sys
import httpx

from ..config.constants import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT
from ..config.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Steward CLI")
    parser.add_argument("--host", default=DEFAULT_DAEMON_HOST, help="Daemon host")
    parser.add_argument("--port", type=int, default=DEFAULT_DAEMON_PORT, help="Daemon port")

    subparsers = parser.add_subparsers(dest="command")

    # Health
    subparsers.add_parser("health", help="Check daemon health")

    # List models
    subparsers.add_parser("models", help="List available NVIDIA NIM models")

    # List sessions
    subparsers.add_parser("sessions", help="List active and past sessions")

    # Create session
    create_parser = subparsers.add_parser("create", help="Create and start new autonomous engineering session")
    create_parser.add_argument("task", help="Engineering task prompt")
    create_parser.add_argument("--model", help="Planner/Actor model to use")

    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    if args.command == "health":
        try:
            resp = httpx.get(f"{base_url}/health", timeout=5.0)
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error connecting to daemon: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "models":
        try:
            resp = httpx.get(f"{base_url}/api/v1/models", timeout=10.0)
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error fetching models: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "sessions":
        try:
            resp = httpx.get(f"{base_url}/api/v1/sessions", timeout=5.0)
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error fetching sessions: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "create":
        try:
            payload = {"task": args.task}
            if args.model:
                payload["model"] = args.model
            resp = httpx.post(f"{base_url}/api/v1/sessions", json=payload, timeout=10.0)
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error creating session: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
