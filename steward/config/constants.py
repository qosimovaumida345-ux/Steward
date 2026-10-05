"""
Constants for Steward (Steward).
"""

from enum import Enum
from pathlib import Path

# API Gateways
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Primary Models (Optimized for NVIDIA Endpoint)
DEFAULT_PLANNER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"  # Orchestrator & high-level planner
DEFAULT_ACTOR_MODEL = "deepseek-ai/deepseek-v4.1-flash"       # #1 Workhorse coder (207 t/s, 1M context)
DEFAULT_HEAVY_MODEL = "moonshotai/kimi-k3"                   # Heavy refactor, frontend UI, vision
DEFAULT_AGENT_MODEL = "z-ai/glm-5.3"                         # Agentic workflows & tool routing
DEFAULT_VISION_MODEL = "moonshotai/kimi-k3"                  # Multimodal frontend and screenshot analysis
DEFAULT_COMPACTOR_MODEL = "nv-mistralai/mistral-nemo-12b-instruct"
DEFAULT_FAST_MODEL = "z-ai/glm-5.3-flash"

# Model Fallback Chain
PLANNER_FALLBACK_CHAIN = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "moonshotai/kimi-k3",
    "z-ai/glm-5.3",
    "deepseek-ai/deepseek-v4.1-flash",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
]

ACTOR_FALLBACK_CHAIN = [
    "deepseek-ai/deepseek-v4.1-flash",
    "moonshotai/kimi-k3",
    "z-ai/glm-5.3",
    "mistralai/mistral-large-2-instruct",
    "mistralai/codestral-22b-instruct-v0.1",
]

# Network and Daemon Defaults
DEFAULT_DAEMON_HOST = "127.0.0.1"
DEFAULT_DAEMON_PORT = 8765
DEFAULT_SERVER_URL = "https://steward-backend-iem7.onrender.com"
DEFAULT_RENDER_POSTGRES_DSN = "postgresql://steward_user:A5V80zwYeMQ3oPgc4isy7PMQaB8S6JBV@dpg-db20hugm7kps73e3i5og-a/steward_xnk8"
DEFAULT_WS_PATH = "/api/v1/sessions/{session_id}/ws"
DEFAULT_REPLAY_BATCH_SIZE = 50

# Storage & Journal Defaults
DEFAULT_DATA_DIR = Path.home() / ".steward"
DEFAULT_SQLITE_PATH = DEFAULT_DATA_DIR / "agent_store.db"
DEFAULT_JOURNAL_JSONL_NAME = "timeline.jsonl"
SQLITE_BUSY_TIMEOUT_MS = 5000

# Token Budgeting & Compaction (High-Capacity Engine)
DEFAULT_MAX_OUTPUT_TOKENS = 16_384
MAX_CONTEXT_TOKENS = 1_000_000
WARNING_CONTEXT_TOKENS = 200_000
COMPACT_THRESHOLD_TOKENS = 200_000
TARGET_COMPACT_TOKENS = 100_000
MAX_TOOL_OUTPUT_CHARS = 250_000
MAX_STREAMING_CHUNK_CHARS = 16_384

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
