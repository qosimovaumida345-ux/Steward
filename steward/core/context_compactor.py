"""
Context Compactor and Token Budgeter.
Provides 3-stage token optimization: tool output truncation, reasoning distillation,
and sliding window micro-summarization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..config.constants import (
    COMPACT_THRESHOLD_TOKENS,
    MAX_TOOL_OUTPUT_CHARS,
    TARGET_COMPACT_TOKENS,
)

logger = logging.getLogger(__name__)


class ContextCompactor:
    """Manages LLM context window boundaries and applies multi-stage compaction."""

    def __init__(
        self,
        compact_threshold: int = COMPACT_THRESHOLD_TOKENS,
        target_tokens: int = TARGET_COMPACT_TOKENS,
        max_tool_chars: int = MAX_TOOL_OUTPUT_CHARS,
    ) -> None:
        self.compact_threshold = compact_threshold
        self.target_tokens = target_tokens
        self.max_tool_chars = max_tool_chars

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Rough estimation: 1 token ~= 4 characters."""
        total_chars = 0
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                total_chars += len(str(content))
        return total_chars // 4

    def truncate_tool_output(self, output: str) -> str:
        """Stage 1: Truncate oversized tool outputs preserving head and tail."""
        if len(output) <= self.max_tool_chars:
            return output

        head_len = self.max_tool_chars // 2
        tail_len = self.max_tool_chars // 2
        omitted = len(output) - (head_len + tail_len)
        return (
            output[:head_len]
            + f"\n\n[... Truncated {omitted} characters of output ...]\n\n"
            + output[-tail_len:]
        )

    def distill_messages_for_llm(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 2: Strip internal reasoning tags and sanitize tool calls."""
        sanitized = []
        for m in messages:
            content = m.get("content")
            if isinstance(content, str):
                # Remove think blocks if present in context
                import re
                clean = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                sanitized.append({**m, "content": clean})
            else:
                sanitized.append(m)
        return sanitized

    def compact_history(
        self, messages: List[Dict[str, Any]], preserve_recent_turns: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Stage 3: Sliding window compaction.
        Summarizes older messages while keeping the system prompt and the latest turns untouched.
        """
        current_tokens = self.estimate_tokens(messages)
        if current_tokens < self.compact_threshold or len(messages) <= preserve_recent_turns + 2:
            return messages

        logger.info(
            "Context compaction triggered (tokens=%d, threshold=%d)",
            current_tokens,
            self.compact_threshold,
        )

        system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
        start_idx = 1 if system_msg else 0

        older_messages = messages[start_idx:-preserve_recent_turns]
        recent_messages = messages[-preserve_recent_turns:]

        # Create structured compact summary of older turns
        summary_points = []
        for m in older_messages:
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))
            first_line = content.split("\n")[0][:120]
            summary_points.append(f"- [{role}]: {first_line}")

        compact_summary = (
            "### Summary of Prior Execution History\n"
            + "\n".join(summary_points[:20])
            + f"\n\n(Compacted {len(older_messages)} earlier interaction turns)"
        )

        compacted_messages = []
        if system_msg:
            compacted_messages.append(system_msg)

        compacted_messages.append({"role": "system", "content": compact_summary})
        compacted_messages.extend(recent_messages)

        new_tokens = self.estimate_tokens(compacted_messages)
        logger.info("Context compacted: %d tokens -> %d tokens", current_tokens, new_tokens)
        return compacted_messages
