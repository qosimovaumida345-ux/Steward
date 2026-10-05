"""Brain Subsystem: NVIDIA NIM cognitive orchestration and reasoning."""

from .model_catalog import ModelCatalog, ModelProfile
from .reasoning_parser import RobustReasoningParser, StreamingParserState
from .rate_limiter import NIMRateLimiter, BackoffStrategy
from .prompt_constitution import PROMPT_CONSTITUTION
from .nvidia_client import NvidiaNimClient
from .dual_engine import DualEngineCoordinator, PlanStep, ExecutionPlan

__all__ = [
    "ModelCatalog",
    "ModelProfile",
    "RobustReasoningParser",
    "StreamingParserState",
    "NIMRateLimiter",
    "BackoffStrategy",
    "PROMPT_CONSTITUTION",
    "NvidiaNimClient",
    "DualEngineCoordinator",
    "PlanStep",
    "ExecutionPlan",
]
