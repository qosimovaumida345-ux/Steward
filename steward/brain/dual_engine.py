"""
Dual Engine Step Coordinator: Planner (DeepSeek-R1) + Actor (Llama 3.3 70B).
Orchestrates high-level CoT reasoning distillation and discrete tool execution.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from .nvidia_client import NvidiaNimClient
from .prompt_constitution import (
    ACTOR_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    PROMPT_CONSTITUTION,
)

logger = logging.getLogger(__name__)


class PlanStep(BaseModel):
    step_id: int
    title: str
    description: str
    tool_hint: Optional[str] = None
    verification_criteria: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, failed
    result_summary: Optional[str] = None


class ExecutionPlan(BaseModel):
    goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    raw_reasoning: str = ""
    current_step_index: int = 0

    def current_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self) -> Optional[PlanStep]:
        self.current_step_index += 1
        return self.current_step()

    def is_finished(self) -> bool:
        return self.current_step_index >= len(self.steps)


class DualEngineCoordinator:
    """
    Coordinates the dual-engine synergy:
    1. Planner (DeepSeek-R1) produces architectural plan with CoT.
    2. Context Distiller isolates pure action spec without 30k reasoning tokens.
    3. Actor (Llama 3.3 70B) executes individual step tools.
    """

    def __init__(self, client: Optional[NvidiaNimClient] = None) -> None:
        self.client = client or NvidiaNimClient()

    async def generate_plan(
        self,
        task: str,
        workspace_context: str = "",
        model: Optional[str] = None,
        on_chunk: Optional[Callable[[str, str], None]] = None,
    ) -> ExecutionPlan:
        """
        Invoke DeepSeek-R1 to plan the architectural DAG.
        Captures raw reasoning for UI stream and parses structured plan.
        """
        messages = [
            {"role": "system", "content": f"{PROMPT_CONSTITUTION}\n\n{PLANNER_SYSTEM_PROMPT}"},
            {
                "role": "user",
                "content": f"Task:\n{task}\n\nWorkspace Context:\n{workspace_context}\n\nConstruct your execution plan now.",
            },
        ]

        full_reasoning: list[str] = []
        full_content: list[str] = []

        try:
            async for r_chunk, c_chunk in self.client.stream_chat(
                messages=messages,
                model=model,
                temperature=0.6,
            ):
                if r_chunk:
                    full_reasoning.append(r_chunk)
                if c_chunk:
                    full_content.append(c_chunk)
                if on_chunk:
                    on_chunk(r_chunk, c_chunk)
        except Exception as e:
            logger.warning("Error generating plan via NIM stream (%s), using local fallback planner", e)
            return self._fallback_plan(task, str(e))

        raw_reasoning = "".join(full_reasoning)
        raw_content = "".join(full_content)

        return self._parse_plan_json(raw_content, raw_reasoning, task)

    async def replan_on_failure(
        self,
        task: str,
        failed_step: PlanStep,
        error_output: str,
        model: Optional[str] = None,
        on_chunk: Optional[Callable[[str, str], None]] = None,
    ) -> ExecutionPlan:
        """
        Targeted replanning after verification failure.
        Only feeds the specific error and step context to minimize token waste.
        """
        messages = [
            {"role": "system", "content": f"{PROMPT_CONSTITUTION}\n\n{PLANNER_SYSTEM_PROMPT}"},
            {
                "role": "user",
                "content": (
                    f"Overall Task: {task}\n\n"
                    f"A step failed during execution or test verification:\n"
                    f"Step {failed_step.step_id}: {failed_step.title}\n"
                    f"Description: {failed_step.description}\n\n"
                    f"Error Output / Test Failure:\n{error_output}\n\n"
                    "Analyze the failure root cause and provide an updated plan to fix the issue and verify."
                ),
            },
        ]

        full_reasoning: list[str] = []
        full_content: list[str] = []

        try:
            async for r_chunk, c_chunk in self.client.stream_chat(
                messages=messages,
                model=model,
                temperature=0.4,
            ):
                if r_chunk:
                    full_reasoning.append(r_chunk)
                if c_chunk:
                    full_content.append(c_chunk)
                if on_chunk:
                    on_chunk(r_chunk, c_chunk)
        except Exception as e:
            logger.warning("Error during replan (%s), using local recovery plan", e)
            return self._fallback_plan(f"Fix failure in: {failed_step.title}", error_output)

        raw_reasoning = "".join(full_reasoning)
        raw_content = "".join(full_content)
        return self._parse_plan_json(raw_content, raw_reasoning, task)

    def distill_step_messages_for_actor(
        self,
        plan: ExecutionPlan,
        step: PlanStep,
        previous_results_summary: str = "",
    ) -> List[Dict[str, str]]:
        """
        Distill execution context for Actor.
        Crucial: Omits raw Planner reasoning tokens, providing crisp, clean instructions.
        """
        content = (
            f"Overall Goal: {plan.goal}\n\n"
            f"Current Assigned Step ({step.step_id}/{len(plan.steps)}): {step.title}\n"
            f"Instructions:\n{step.description}\n\n"
        )
        if step.verification_criteria:
            content += f"Verification Requirement:\n{step.verification_criteria}\n\n"
        if previous_results_summary:
            content += f"Previous Steps Summary:\n{previous_results_summary}\n\n"

        content += "Execute this step with the appropriate tools and confirm completion."

        return [
            {"role": "system", "content": f"{PROMPT_CONSTITUTION}\n\n{ACTOR_SYSTEM_PROMPT}"},
            {"role": "user", "content": content},
        ]

    def _parse_plan_json(self, raw_content: str, raw_reasoning: str, original_task: str) -> ExecutionPlan:
        # Match json block ```json ... ``` or raw json
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_content, re.DOTALL)
        json_str = match.group(1) if match else raw_content.strip()

        try:
            data = json.loads(json_str)
            goal = data.get("goal", original_task)
            steps_data = data.get("steps", [])
            steps = [
                PlanStep(
                    step_id=s.get("step_id", idx + 1),
                    title=s.get("title", f"Step {idx + 1}"),
                    description=s.get("description", ""),
                    tool_hint=s.get("tool_hint"),
                    verification_criteria=s.get("verification_criteria"),
                )
                for idx, s in enumerate(steps_data)
            ]
            if not steps:
                steps = self._default_steps(original_task)
            return ExecutionPlan(goal=goal, steps=steps, raw_reasoning=raw_reasoning)
        except Exception:
            # Fallback regex or default plan
            return self._fallback_plan(original_task, raw_content, raw_reasoning)

    def _default_steps(self, task: str) -> List[PlanStep]:
        return [
            PlanStep(
                step_id=1,
                title="Inspect Environment & Workspace",
                description="Analyze relevant code files, dependencies, and configuration.",
                tool_hint="file_tools",
                verification_criteria="Context gathered",
            ),
            PlanStep(
                step_id=2,
                title="Implement Solution",
                description=f"Carry out necessary code modifications to satisfy: {task}",
                tool_hint="file_edit",
                verification_criteria="Code written cleanly",
            ),
            PlanStep(
                step_id=3,
                title="Run Tests and Verify",
                description="Run pytest test suite and verify edge cases.",
                tool_hint="terminal_tools",
                verification_criteria="All tests pass cleanly",
            ),
        ]

    def _fallback_plan(self, task: str, details: str, reasoning: str = "") -> ExecutionPlan:
        return ExecutionPlan(
            goal=task,
            steps=self._default_steps(task),
            raw_reasoning=reasoning or f"Direct execution planned for: {details}",
        )
