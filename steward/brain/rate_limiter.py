"""
Token-bucket rate limiter and exponential backoff failover strategy for NVIDIA NIM.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BackoffStrategy:
    """Exponential backoff with full jitter to avoid thundering herd."""

    def __init__(
        self,
        base_seconds: float = 1.0,
        max_seconds: float = 30.0,
        factor: float = 2.0,
        jitter: bool = True,
    ) -> None:
        self.base_seconds = base_seconds
        self.max_seconds = max_seconds
        self.factor = factor
        self.jitter = jitter

    def compute_delay(self, attempt: int) -> float:
        calculated = min(self.max_seconds, self.base_seconds * (self.factor ** attempt))
        if self.jitter:
            return random.uniform(0.0, calculated)
        return calculated


class NIMRateLimiter:
    """
    Coordinates request limits across models and handles automatic failover
    when a model experiences rate-limiting (429) or transient degradation (503).
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100_000,
        backoff: Optional[BackoffStrategy] = None,
    ) -> None:
        self.rpm = requests_per_minute
        self.tpm = tokens_per_minute
        self.backoff = backoff or BackoffStrategy()
        self._lock = asyncio.Lock()
        self._request_timestamps: list[float] = []
        self._model_failure_counts: Dict[str, int] = {}
        self._model_cooldown_until: Dict[str, float] = {}

    async def acquire(self, estimated_tokens: int = 100) -> None:
        """Wait if rate limits would be exceeded."""
        async with self._lock:
            now = time.monotonic()
            # Clean timestamps older than 60 seconds
            self._request_timestamps = [t for t in self._request_timestamps if now - t < 60.0]

            if len(self._request_timestamps) >= self.rpm:
                sleep_time = 60.0 - (now - self._request_timestamps[0]) + 0.1
                if sleep_time > 0:
                    logger.warning("Local rate limit hit. Throttling for %.2fs", sleep_time)
                    await asyncio.sleep(sleep_time)

            self._request_timestamps.append(time.monotonic())

    def record_success(self, model: str) -> None:
        """Reset failure streak on successful response."""
        self._model_failure_counts[model] = 0
        if model in self._model_cooldown_until:
            del self._model_cooldown_until[model]

    def record_failure(self, model: str, status_code: int = 429) -> float:
        """
        Record a rate limit or transient failure.
        Returns the recommended backoff delay in seconds.
        """
        attempts = self._model_failure_counts.get(model, 0) + 1
        self._model_failure_counts[model] = attempts
        delay = self.backoff.compute_delay(attempts)
        self._model_cooldown_until[model] = time.monotonic() + delay
        logger.warning(
            "Model %s failed (status=%d, streak=%d). Cooling down for %.2fs",
            model,
            status_code,
            attempts,
            delay,
        )
        return delay

    def is_model_available(self, model: str) -> bool:
        """Check if model is currently out of cooldown."""
        cooldown = self._model_cooldown_until.get(model, 0.0)
        return time.monotonic() >= cooldown

    def select_available_model(self, fallback_chain: List[str]) -> str:
        """Select first available model in fallback chain, or primary if all cooling down."""
        for model in fallback_chain:
            if self.is_model_available(model):
                return model
        # If all are cooling down, return the one that finishes earliest
        earliest = min(fallback_chain, key=lambda m: self._model_cooldown_until.get(m, 0.0))
        return earliest
