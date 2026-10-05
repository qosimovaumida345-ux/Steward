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


def test_resolve_server_endpoints_trailing_slashes():
    http_base, ws_base = resolve_server_endpoints("steward-backend-iem7.onrender.com/")
    assert http_base == "https://steward-backend-iem7.onrender.com"
    assert ws_base == "wss://steward-backend-iem7.onrender.com"


def test_pg8000_query_formatting():
    from steward.storage.render_postgres import _format_pg8000_query

    sql = "INSERT INTO test (a, b, c) VALUES (%s, %s, %s::jsonb)"
    params = ("id1", "title", "{}")
    new_sql, kwargs = _format_pg8000_query(sql, params)
    assert new_sql == "INSERT INTO test (a, b, c) VALUES (:p0, :p1, :p2::jsonb)"
    assert kwargs == {"p0": "id1", "p1": "title", "p2": "{}"}

    # Test mismatch error
    with pytest.raises(ValueError):
        _format_pg8000_query(sql, ("id1", "title"))


def test_daemon_host_sanitization_when_url_provided(monkeypatch):
    monkeypatch.setenv("STEWARD_HOST", "https://steward-backend-iem7.onrender.com")
    monkeypatch.delenv("STEWARD_SERVER_URL", raising=False)
    monkeypatch.delenv("STEWARD_DAEMON_HOST", raising=False)

    s = Settings()
    # daemon_host must NOT be a URL with https://
    assert s.daemon_host == "127.0.0.1"
    assert s.server_url == "https://steward-backend-iem7.onrender.com"

