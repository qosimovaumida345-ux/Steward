"""
Constants for Steward (Steward).
"""

from enum import Enum
from pathlib import Path

# API Gateways
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Primary Models
DEFAULT_PLANNER_MODEL = "deepseek-ai/deepseek-r1"
DEFAULT_ACTOR_MODEL = "meta/llama-3.3-70b-instruct"
DEFAULT_COMPACTOR_MODEL = "meta/llama-3.1-8b-instruct"
DEFAULT_FAST_MODEL = "meta/llama-3.1-70b-instruct"

# Model Fallback Chain
PLANNER_FALLBACK_CHAIN = [
    "deepseek-ai/deepseek-r1",
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
]

ACTOR_FALLBACK_CHAIN = [
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/llama-3.1-70b-instruct",
]

# Network and Daemon Defaults
DEFAULT_DAEMON_HOST = "127.0.0.1"
DEFAULT_DAEMON_PORT = 8765
DEFAULT_WS_PATH = "/api/v1/sessions/{session_id}/ws"
DEFAULT_REPLAY_BATCH_SIZE = 50

# Storage & Journal Defaults
DEFAULT_DATA_DIR = Path.home() / ".steward"
DEFAULT_SQLITE_PATH = DEFAULT_DATA_DIR / "agent_store.db"
DEFAULT_JOURNAL_JSONL_NAME = "timeline.jsonl"
SQLITE_BUSY_TIMEOUT_MS = 5000

# Token Budgeting & Compaction
MAX_CONTEXT_TOKENS = 128_000
WARNING_CONTEXT_TOKENS = 96_000
COMPACT_THRESHOLD_TOKENS = 80_000
TARGET_COMPACT_TOKENS = 40_000
MAX_TOOL_OUTPUT_CHARS = 16_000
MAX_STREAMING_CHUNK_CHARS = 4096

# Timeouts & Retries
HTTP_TIMEOUT_SECONDS = 90.0
STREAM_TIMEOUT_SECONDS = 180.0
MAX_RETRY_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0

# Security Boundaries
SAFE_COMMAND_TIMEOUT_SECONDS = 120.0
JOB_OBJECT_NAME_PREFIX = "Steward_Job_"


class PermissionMode(str, Enum):
    AUTONOMOUS = "autonomous"     # Auto-approves benign and standard developer tools
    GUARDED = "guarded"           # Asks approval for high-risk operations (destructive, network, secrets)
    SANDBOXED = "sandboxed"       # Read-only + strictly isolated execution


class SessionState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TERMINATED = "TERMINATED"


class EventType(str, Enum):
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    THINKING_CHUNK = "thinking_chunk"
    CONTENT_CHUNK = "content_chunk"
    PLAN_GENERATED = "plan_generated"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_APPROVED = "tool_call_approved"
    TOOL_CALL_REJECTED = "tool_call_rejected"
    TOOL_CALL_RESULT = "tool_call_result"
    TERMINAL_OUTPUT = "terminal_output"
    FILE_DIFF = "file_diff"
    ERROR = "error"
    STATUS_CHANGED = "status_changed"
    SUBAGENT_DISPATCHED = "subagent_dispatched"
    SUBAGENT_FINISHED = "subagent_finished"
    SYNC_ACK = "sync_ack"
