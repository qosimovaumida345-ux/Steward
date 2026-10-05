"""
Unit tests for NVIDIA NIM client, ModelCatalog, and RateLimiter.
"""

import pytest
from steward.brain.model_catalog import ModelCatalog, ModelProfile
from steward.brain.rate_limiter import BackoffStrategy, NIMRateLimiter
from steward.brain.nvidia_client import NvidiaNimClient


def test_model_catalog_defaults():
    catalog = ModelCatalog()
    profile = catalog.get_profile("deepseek-ai/deepseek-r1")
    assert profile is not None
    assert profile.is_reasoning_model is True
    assert profile.recommended_role == "planner"

    actor_profile = catalog.get_profile("meta/llama-3.3-70b-instruct")
    assert actor_profile is not None
    assert actor_profile.supports_tools is True
    assert actor_profile.recommended_role == "actor"


def test_model_catalog_dynamic_update():
    catalog = ModelCatalog()
    raw = [
        {"id": "nvidia/new-test-model"},
        {"id": "deepseek-ai/deepseek-r1"},
    ]
    catalog.update_from_nim_models_list(raw)
    p = catalog.get_profile("nvidia/new-test-model")
    assert p is not None
    assert p.model_id == "nvidia/new-test-model"


def test_backoff_strategy_jitter():
    backoff = BackoffStrategy(base_seconds=1.0, max_seconds=10.0, factor=2.0, jitter=True)
    delay = backoff.compute_delay(attempt=2)
    assert 0.0 <= delay <= 4.0


def test_rate_limiter_cooldown_and_failover():
    limiter = NIMRateLimiter()
    model_a = "model_a"
    model_b = "model_b"

    assert limiter.is_model_available(model_a) is True

    # Record failure on model_a
    delay = limiter.record_failure(model_a, status_code=429)
    assert delay > 0
    assert limiter.is_model_available(model_a) is False

    # Failover to model_b
    selected = limiter.select_available_model([model_a, model_b])
    assert selected == model_b

    # Reset success
    limiter.record_success(model_a)
    assert limiter.is_model_available(model_a) is True


@pytest.mark.asyncio
async def test_nvidia_client_offline_simulation():
    # When api_key is None/empty, client provides simulated response without crashing
    client = NvidiaNimClient(api_key="")
    chunks_r = []
    chunks_c = []
    async for r, c in client.stream_chat([{"role": "user", "content": "hi"}]):
        if r:
            chunks_r.append(r)
        if c:
            chunks_c.append(c)

    full_r = "".join(chunks_r)
    full_c = "".join(chunks_c)
    assert "Analyzing" in full_r or "offline" in full_r or "Ready" in full_c
