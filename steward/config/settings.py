"""
Settings management for Steward.
Loads from environment variables and local .env files.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_ACTOR_MODEL,
    DEFAULT_COMPACTOR_MODEL,
    DEFAULT_DAEMON_HOST,
    DEFAULT_DAEMON_PORT,
    DEFAULT_DATA_DIR,
    DEFAULT_PLANNER_MODEL,
    DEFAULT_RENDER_POSTGRES_DSN,
    DEFAULT_SERVER_URL,
    DEFAULT_SQLITE_PATH,
    NVIDIA_NIM_BASE_URL,
    PermissionMode,
)

# Load existing .env files if present (check current dir, executable dir, MEIPASS, or project root)
_candidate_envs = [
    Path.cwd() / ".env",
    Path(sys.executable).parent / ".env",
    (Path(getattr(sys, "_MEIPASS", "")) / ".env") if hasattr(sys, "_MEIPASS") else None,
    Path(__file__).resolve().parent.parent.parent / ".env",
]
for _env_path in _candidate_envs:
    if _env_path and _env_path.exists():
        load_dotenv(dotenv_path=_env_path, override=False)
        break
else:
    load_dotenv(override=False)


def _resolve_server_url() -> str:
    url = os.getenv("STEWARD_SERVER_URL")
    if url:
        return url
    host = os.getenv("STEWARD_HOST")
    if host and "://" in host:
        return host
    return DEFAULT_SERVER_URL


def _resolve_daemon_host() -> str:
    daemon_host = os.getenv("STEWARD_DAEMON_HOST")
    if daemon_host:
        return daemon_host
    host = os.getenv("STEWARD_HOST")
    # If STEWARD_HOST is a full URL, do not use it as local bind host
    if host and "://" not in host:
        return host
    return DEFAULT_DAEMON_HOST


class Settings(BaseModel):
    # NVIDIA NIM Brain
    nvidia_api_key: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_API_KEY", "")
    )
    nvidia_base_url: str = Field(
        default_factory=lambda: os.getenv("NVIDIA_NIM_BASE_URL", NVIDIA_NIM_BASE_URL)
    )
    planner_model: str = Field(
        default_factory=lambda: os.getenv("PLANNER_MODEL", DEFAULT_PLANNER_MODEL)
    )
    actor_model: str = Field(
        default_factory=lambda: os.getenv("ACTOR_MODEL", DEFAULT_ACTOR_MODEL)
    )
    compactor_model: str = Field(
        default_factory=lambda: os.getenv("COMPACTOR_MODEL", DEFAULT_COMPACTOR_MODEL)
    )

    # Cloud Storage / Render PostgreSQL
    render_postgres_dsn: Optional[str] = Field(
        default_factory=lambda: os.getenv("RENDER_POSTGRES_DSN") or os.getenv("DATABASE_URL") or DEFAULT_RENDER_POSTGRES_DSN
    )
    render_sync_enabled: bool = Field(
        default_factory=lambda: os.getenv("RENDER_SYNC_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # Server / Render Cloud Endpoint
    server_url: str = Field(
        default_factory=_resolve_server_url
    )

    # Local Persistence
    data_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("STEWARD_DATA_DIR") or str(DEFAULT_DATA_DIR))
    )
    sqlite_path: Path = Field(
        default_factory=lambda: Path(os.getenv("STEWARD_SQLITE_PATH") or str(DEFAULT_SQLITE_PATH))
    )

    # Network / Daemon
    daemon_host: str = Field(
        default_factory=_resolve_daemon_host
    )
    daemon_port: int = Field(
        default_factory=lambda: int(os.getenv("STEWARD_PORT") or str(DEFAULT_DAEMON_PORT))
    )

    # Security
    permission_mode: PermissionMode = Field(
        default_factory=lambda: PermissionMode(
            os.getenv("STEWARD_PERMISSION_MODE") or PermissionMode.GUARDED.value
        )
    )
    workspace_root: Path = Field(
        default_factory=lambda: Path(os.getenv("STEWARD_WORKSPACE", os.getcwd())).resolve()
    )

    def ensure_directories(self) -> None:
        """Create required runtime folders if not present."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached application settings instance."""
    s = Settings()
    s.ensure_directories()
    return s
