"""
Model Catalog for NVIDIA NIM models with capabilities and limits.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    model_id: str
    display_name: str
    max_context_tokens: int = 128_000
    max_output_tokens: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    is_reasoning_model: bool = False
    recommended_role: str = "actor"  # planner, actor, compactor, general
    description: str = ""


class ModelCatalog:
    """Manages available NVIDIA NIM models, their capabilities, and runtime selection."""

    DEFAULT_PROFILES: Dict[str, ModelProfile] = {
        "deepseek-ai/deepseek-r1": ModelProfile(
            model_id="deepseek-ai/deepseek-r1",
            display_name="DeepSeek-R1 (Architectural Reasoning)",
            max_context_tokens=128_000,
            max_output_tokens=8192,
            supports_tools=False,
            supports_vision=False,
            is_reasoning_model=True,
            recommended_role="planner",
            description="Leading reasoning model emitting <think> tags for autonomous DAG planning.",
        ),
        "meta/llama-3.3-70b-instruct": ModelProfile(
            model_id="meta/llama-3.3-70b-instruct",
            display_name="Llama 3.3 70B Instruct (Tool Actor)",
            max_context_tokens=128_000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="High precision native function and tool calling model with strict instruction following.",
        ),
        "nvidia/llama-3.1-nemotron-70b-instruct": ModelProfile(
            model_id="nvidia/llama-3.1-nemotron-70b-instruct",
            display_name="Nemotron 70B Instruct (High Precision)",
            max_context_tokens=128_000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="NVIDIA tuned Llama model for advanced coding and tool synthesis.",
        ),
        "meta/llama-3.1-8b-instruct": ModelProfile(
            model_id="meta/llama-3.1-8b-instruct",
            display_name="Llama 3.1 8B Instruct (Micro-Compactor)",
            max_context_tokens=128_000,
            max_output_tokens=2048,
            supports_tools=False,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="compactor",
            description="Lightweight and ultra-fast model for timeline distillation and sliding window compaction.",
        ),
        "meta/llama-3.1-70b-instruct": ModelProfile(
            model_id="meta/llama-3.1-70b-instruct",
            display_name="Llama 3.1 70B Instruct",
            max_context_tokens=128_000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Reliable fallback for tool execution and general code synthesis.",
        ),
    }

    def __init__(self) -> None:
        self._profiles: Dict[str, ModelProfile] = dict(self.DEFAULT_PROFILES)

    def get_profile(self, model_id: str) -> Optional[ModelProfile]:
        return self._profiles.get(model_id)

    def list_all(self) -> List[ModelProfile]:
        return list(self._profiles.values())

    def get_by_role(self, role: str) -> List[ModelProfile]:
        return [p for p in self._profiles.values() if p.recommended_role == role]

    def register_or_update(self, profile: ModelProfile) -> None:
        self._profiles[profile.model_id] = profile

    def update_from_nim_models_list(self, raw_models: List[dict]) -> None:
        """Dynamically populate catalog from NVIDIA NIM /v1/models response."""
        for item in raw_models:
            mid = item.get("id")
            if not mid:
                continue
            if mid not in self._profiles:
                is_reasoning = "r1" in mid.lower() or "reason" in mid.lower()
                role = "planner" if is_reasoning else "actor"
                self._profiles[mid] = ModelProfile(
                    model_id=mid,
                    display_name=mid.split("/")[-1].replace("-", " ").title(),
                    supports_tools=not is_reasoning,
                    is_reasoning_model=is_reasoning,
                    recommended_role=role,
                    description=f"Dynamically discovered model from NVIDIA NIM API: {mid}",
                )
