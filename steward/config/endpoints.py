"""
Endpoint resolution utilities for Steward.
Provides robust HTTP and WebSocket URL construction for local and cloud deployments (e.g. Render).
"""
from __future__ import annotations

import urllib.parse
from typing import Tuple

DEFAULT_RENDER_HOST = "steward-backend-iem7.onrender.com"
DEFAULT_RENDER_SERVER_URL = "https://steward-backend-iem7.onrender.com"


def resolve_server_endpoints(
    host_or_url: str = DEFAULT_RENDER_SERVER_URL,
    port: int | None = None,
) -> Tuple[str, str]:
    """
    Given a host, IP, or full URL, return (http_base_url, ws_base_url).

    Examples:
        "https://steward-backend-iem7.onrender.com"
            -> ("https://steward-backend-iem7.onrender.com", "wss://steward-backend-iem7.onrender.com")
        "steward-backend-iem7.onrender.com"
            -> ("https://steward-backend-iem7.onrender.com", "wss://steward-backend-iem7.onrender.com")
        "127.0.0.1", 8765
            -> ("http://127.0.0.1:8765", "ws://127.0.0.1:8765")
        "http://localhost:8765"
            -> ("http://localhost:8765", "ws://localhost:8765")
    """
    raw = (host_or_url or "").strip()
    if not raw:
        raw = DEFAULT_RENDER_SERVER_URL

    # If scheme is already present
    if "://" in raw:
        parsed = urllib.parse.urlsplit(raw)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc
        path = parsed.path.rstrip("/")

        if scheme in ("https", "wss"):
            http_base = f"https://{netloc}{path}"
            ws_base = f"wss://{netloc}{path}"
        else:
            http_base = f"http://{netloc}{path}"
            ws_base = f"ws://{netloc}{path}"
        return http_base, ws_base

    # If no scheme is present:
    # Check if host is a cloud domain (Render, Heroku, etc.) or port is 443
    if "onrender.com" in raw.lower() or port == 443:
        http_base = f"https://{raw}"
        ws_base = f"wss://{raw}"
    else:
        # Standard local host
        p = port if port is not None else 8765
        http_base = f"http://{raw}:{p}"
        ws_base = f"ws://{raw}:{p}"

    return http_base, ws_base
