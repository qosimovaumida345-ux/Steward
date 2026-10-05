"""
Unit tests for DualEngineCoordinator (DeepSeek-R1 Planner + Llama 3.3 Actor).
"""

import pytest
from steward.brain.dual_engine import DualEngineCoordinator, ExecutionPlan, PlanStep


def test_execution_plan_advancement():
    steps = [
        PlanStep(step_id=1, title="Step 1", description="Do 1"),
        PlanStep(step_id=2, title="Step 2", description="Do 2"),
    ]
    plan = ExecutionPlan(goal="Test Goal", steps=steps, raw_reasoning="Deep reasoning")

    assert plan.current_step().step_id == 1
    assert not plan.is_finished()

    plan.advance()
    assert plan.current_step().step_id == 2

    plan.advance()
    assert plan.is_finished()


def test_distill_context_for_actor_omits_raw_cot():
    coordinator = DualEngineCoordinator()
    step = PlanStep(
        step_id=1,
        title="Implement File Storage",
        description="Write SQLite code",
        verification_criteria="Tests pass",
    )
    plan = ExecutionPlan(
        goal="Build Storage",
        steps=[step],
        raw_reasoning="<think>Very long 20,000 token internal thought trace</think>",
    )

    actor_messages = coordinator.distill_step_messages_for_actor(
        plan, step, previous_results_summary="Previous completed"
    )

    # Verify that raw reasoning tokens are completely absent from actor prompt
    user_content = actor_messages[1]["content"]
    assert "<think>" not in user_content
    assert "Very long 20,000 token" not in user_content
    assert "Implement File Storage" in user_content
    assert "Write SQLite code" in user_content


@pytest.mark.asyncio
async def test_replan_on_failure_flow():
    coordinator = DualEngineCoordinator()
    step = PlanStep(step_id=1, title="Run Test", description="Run pytest")
    new_plan = await coordinator.replan_on_failure(
        task="Fix code",
        failed_step=step,
        error_output="AssertionError: Expected 5 got 4",
    )

    assert new_plan is not None
    assert len(new_plan.steps) > 0
