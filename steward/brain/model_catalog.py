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
        "mistralai/mistral-large-2-instruct": ModelProfile(
            model_id="mistralai/mistral-large-2-instruct",
            display_name="Mistral Large 2 (123B Flagship Coder & Agent)",
            max_context_tokens=128_000,
            max_output_tokens=8192,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Flagship 123B model with elite coding proficiency, native tool calling, and 128k context.",
        ),
        "mistralai/codestral-22b-instruct-v0.1": ModelProfile(
            model_id="mistralai/codestral-22b-instruct-v0.1",
            display_name="Codestral 22B (Specialized Code Engine)",
            max_context_tokens=32_768,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Dedicated code intelligence trained on 80+ programming languages with fill-in-the-middle support.",
        ),
        "deepseek-ai/deepseek-v4.1-flash": ModelProfile(
            model_id="deepseek-ai/deepseek-v4.1-flash",
            display_name="DeepSeek V4.1 Flash (#1 Workhorse Coder)",
            max_context_tokens=1_000_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Ultra-fast workhorse coding engine (~207 t/s) with 90.6 Terminal-Bench score and 1M context.",
        ),
        "nvidia/nemotron-3-ultra-550b-a55b": ModelProfile(
            model_id="nvidia/nemotron-3-ultra-550b-a55b",
            display_name="Nemotron 3 Ultra (550B Master Orchestrator)",
            max_context_tokens=1_000_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=True,
            recommended_role="planner",
            description="550B Master Orchestrator for system-wide planning, task decomposition, and agent management.",
        ),
        "nvidia/llama-3.1-nemotron-ultra-253b-v1": ModelProfile(
            model_id="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            display_name="Nemotron Ultra 253B (Ultra Reasoning)",
            max_context_tokens=128_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=True,
            recommended_role="planner",
            description="253-Billion parameter reasoning heavyweight optimized for complex multi-turn logic.",
        ),
        "meta/llama-3.2-90b-vision-instruct": ModelProfile(
            model_id="meta/llama-3.2-90b-vision-instruct",
            display_name="Llama 3.2 90B Vision (Computer Use Eye)",
            max_context_tokens=128_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=True,
            is_reasoning_model=False,
            recommended_role="actor",
            description="90B multimodal vision model with high resolution screenshot parsing for Computer Use.",
        ),
        "nv-mistralai/mistral-nemo-12b-instruct": ModelProfile(
            model_id="nv-mistralai/mistral-nemo-12b-instruct",
            display_name="Mistral NeMo 12B (Fast 128k Compactor)",
            max_context_tokens=128_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="compactor",
            description="High-speed 12B model with full 128k context window ideal for background summarization.",
        ),
        "mistralai/mixtral-8x22b-v0.1": ModelProfile(
            model_id="mistralai/mixtral-8x22b-v0.1",
            display_name="Mixtral 8x22B (176B MoE Powerhouse)",
            max_context_tokens=65_536,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Sparse Mixture of Experts combining 176B total parameters with high throughput.",
        ),
        "meta/codellama-70b": ModelProfile(
            model_id="meta/codellama-70b",
            display_name="CodeLlama 70B (Meta Code Specialist)",
            max_context_tokens=100_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Meta specialized 70B programming model with 100k context window.",
        ),
        "z-ai/glm-5.3": ModelProfile(
            model_id="z-ai/glm-5.3",
            display_name="GLM 5.3 (Agentic Tool Specialist)",
            max_context_tokens=1_000_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=True,
            recommended_role="actor",
            description="Agentic tool specialist (88.2 Terminal-Bench) with token-efficient subagent routing.",
        ),
        "moonshotai/kimi-k3": ModelProfile(
            model_id="moonshotai/kimi-k3",
            display_name="Kimi K3 (Frontend, UI & Deep Thinker)",
            max_context_tokens=1_000_000,
            max_output_tokens=16_384,
            supports_tools=True,
            supports_vision=True,
            is_reasoning_model=True,
            recommended_role="actor",
            description="Top frontend & multimodal powerhouse (88.3 Terminal-Bench, SWE-Marathon leader) for complex UI & refactoring.",
        ),
        "google/gemma-4-31b-it": ModelProfile(
            model_id="google/gemma-4-31b-it",
            display_name="Gemma 4 31B IT (Google High-Efficiency)",
            max_context_tokens=128_000,
            max_output_tokens=4096,
            supports_tools=True,
            supports_vision=False,
            is_reasoning_model=False,
            recommended_role="actor",
            description="Google latest instruction-tuned 31B model with state-of-the-art efficiency.",
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
