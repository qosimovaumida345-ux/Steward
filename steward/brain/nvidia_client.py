"""
NVIDIA NIM Async API Client.
Supports SSE streaming, tool schemas, dynamic model discovery, and automatic failover.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from ..config.constants import (
    DEFAULT_ACTOR_MODEL,
    DEFAULT_PLANNER_MODEL,
    HTTP_TIMEOUT_SECONDS,
    NVIDIA_NIM_BASE_URL,
    STREAM_TIMEOUT_SECONDS,
)
from ..config.settings import get_settings
from .model_catalog import ModelCatalog
from .rate_limiter import NIMRateLimiter
from .reasoning_parser import RobustReasoningParser

logger = logging.getLogger(__name__)


class NvidiaNimClient:
    """Async client for NVIDIA NIM OpenAI-compatible API endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limiter: Optional[NIMRateLimiter] = None,
        catalog: Optional[ModelCatalog] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.nvidia_api_key
        self.base_url = (base_url or settings.nvidia_base_url).rstrip("/")
        self.rate_limiter = rate_limiter or NIMRateLimiter()
        self.catalog = catalog or ModelCatalog()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def list_models(self) -> List[Dict[str, Any]]:
        """Query /v1/models to dynamically discover models available on the NIM endpoint."""
        url = f"{self.base_url}/models"
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            try:
                resp = await client.get(url, headers=self._headers())
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    self.catalog.update_from_nim_models_list(data)
                    return data
                else:
                    logger.warning("Failed to fetch models from NIM: status %d", resp.status_code)
                    return [p.model_dump() for p in self.catalog.list_all()]
            except Exception as e:
                logger.warning("Error discovering NIM models (%s), using default catalog", e)
                return [p.model_dump() for p in self.catalog.list_all()]

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        Stream chat completion. Yields (reasoning_chunk, content_chunk).
        Uses RobustReasoningParser to cleanly separate <think> CoT tokens.
        """
        target_model = model or DEFAULT_PLANNER_MODEL
        await self.rate_limiter.acquire(estimated_tokens=500)

        # In case API key is not supplied (e.g. offline/mock testing), return a fallback simulation
        if not self.api_key:
            logger.info("No NVIDIA API key configured, generating simulated response.")
            simulated_text = (
                "<think>Analyzing user request in offline simulation mode.</think>\n"
                "System initialized in autonomous mode. Ready to receive commands."
            )
            parser = RobustReasoningParser()
            r, c = parser.feed(simulated_text)
            fr, fc = parser.flush()
            yield r + fr, c + fc
            return

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        parser = RobustReasoningParser()

        async with httpx.AsyncClient(timeout=STREAM_TIMEOUT_SECONDS) as client:
            try:
                async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        self.rate_limiter.record_failure(target_model, response.status_code)
                        raise RuntimeError(
                            f"NIM Stream Error {response.status_code}: {body.decode('utf-8', errors='ignore')}"
                        )

                    self.rate_limiter.record_success(target_model)

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data_json = json.loads(data_str)
                            choices = data_json.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            # Some models emit reasoning_content field directly
                            reasoning_content = delta.get("reasoning_content", "")

                            if reasoning_content:
                                yield reasoning_content, ""
                            if content:
                                r_chunk, c_chunk = parser.feed(content)
                                if r_chunk or c_chunk:
                                    yield r_chunk, c_chunk
                        except json.JSONDecodeError:
                            continue

                    flush_r, flush_c = parser.flush()
                    if flush_r or flush_c:
                        yield flush_r, flush_c

            except Exception as exc:
                self.rate_limiter.record_failure(target_model, 500)
                raise exc

    async def generate_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Non-streaming chat completion with tool calling support."""
        target_model = model or DEFAULT_ACTOR_MODEL
        await self.rate_limiter.acquire(estimated_tokens=500)

        if not self.api_key:
            return {
                "role": "assistant",
                "content": "Simulated response (No NVIDIA API key configured).",
                "tool_calls": [],
            }

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=self._headers(), json=payload)
            if resp.status_code != 200:
                self.rate_limiter.record_failure(target_model, resp.status_code)
                raise RuntimeError(f"NIM Error {resp.status_code}: {resp.text}")

            self.rate_limiter.record_success(target_model)
            data = resp.json()
            choice = data["choices"][0]["message"]
            return choice
