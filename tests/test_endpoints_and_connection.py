"""
Tests for server endpoint resolution and client connection setup.
Verifies seamless HTTPS and WSS resolution for Render Cloud and local environments.
"""

import pytest

from steward.config.constants import DEFAULT_RENDER_POSTGRES_DSN, DEFAULT_SERVER_URL
from steward.config.endpoints import resolve_server_endpoints
from steward.config.settings import Settings
from steward.client.client_connection import DaemonClientConnection


def test_resolve_server_endpoints_render_https():
    http_base, ws_base = resolve_server_endpoints("https://steward-backend-iem7.onrender.com")
    assert http_base == "https://steward-backend-iem7.onrender.com"
    assert ws_base == "wss://steward-backend-iem7.onrender.com"


def test_resolve_server_endpoints_render_raw_domain():
    http_base, ws_base = resolve_server_endpoints("steward-backend-iem7.onrender.com")
    assert http_base == "https://steward-backend-iem7.onrender.com"
    assert ws_base == "wss://steward-backend-iem7.onrender.com"


def test_resolve_server_endpoints_local_host_port():
    http_base, ws_base = resolve_server_endpoints("127.0.0.1", 8765)
    assert http_base == "http://127.0.0.1:8765"
    assert ws_base == "ws://127.0.0.1:8765"


def test_resolve_server_endpoints_default():
    http_base, ws_base = resolve_server_endpoints("")
    assert "steward-backend-iem7.onrender.com" in http_base
    assert http_base.startswith("https://")
    assert ws_base.startswith("wss://")


def test_settings_defaults():
    s = Settings()
    assert s.server_url is not None
    assert "onrender.com" in s.server_url
    assert s.render_postgres_dsn == DEFAULT_RENDER_POSTGRES_DSN


def test_daemon_client_connection_urls():
    conn = DaemonClientConnection(
        session_id="sess_123",
        host="https://steward-backend-iem7.onrender.com",
    )
    assert conn.http_base == "https://steward-backend-iem7.onrender.com"
    assert conn.ws_base == "wss://steward-backend-iem7.onrender.com"
    expected_ws_url = f"{conn.ws_base}/api/v1/sessions/sess_123/ws"
    assert expected_ws_url == "wss://steward-backend-iem7.onrender.com/api/v1/sessions/sess_123/ws"
