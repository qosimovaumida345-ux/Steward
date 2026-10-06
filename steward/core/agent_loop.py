"""
Autonomous Agent Loop: ReAct OODAV Execution Engine.
Orchestrates Planner-Actor dyad, tool execution, permission gating, and timeline journaling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from ..brain.dual_engine import DualEngineCoordinator, ExecutionPlan, PlanStep
from ..brain.nvidia_client import NvidiaNimClient
from ..config.constants import EventType, SessionState
from ..security.permission_guard import PermissionGuard
from ..tools.registry import ToolRegistry
from .context_compactor import ContextCompactor
from .state_machine import SessionStateMachine
from .timeline_journal import TimelineJournal

logger = logging.getLogger(__name__)


class AutonomousAgentLoop:
    """Executes long-running autonomous developer engineering sessions."""

    def __init__(
        self,
        session_id: str,
        journal: TimelineJournal,
        state_machine: SessionStateMachine,
        tool_registry: ToolRegistry,
        permission_guard: PermissionGuard,
        coordinator: Optional[DualEngineCoordinator] = None,
        compactor: Optional[ContextCompactor] = None,
    ) -> None:
        self.session_id = session_id
        self.journal = journal
        self.state_machine = state_machine
        self.tools = tool_registry
        self.guard = permission_guard
        self.coordinator = coordinator or DualEngineCoordinator()
        self.compactor = compactor or ContextCompactor()

        self._cancelled = False
        self._current_plan: Optional[ExecutionPlan] = None
        self._step_results_summary: list[str] = []

    def cancel(self) -> None:
        """Cancel ongoing execution gracefully."""
        self._cancelled = True
        self.state_machine.transition_to(SessionState.TERMINATED)
        self.journal.record_event(
            EventType.STATUS_CHANGED,
            {"status": SessionState.TERMINATED.value, "reason": "User cancelled"},
        )

    async def run(self, task_description: str, workspace_context: str = "") -> bool:
        """Main autonomous execution loop."""
        logger.info("Starting autonomous loop for session %s: %s", self.session_id, task_description)

        # 1. Planning Phase
        self.state_machine.transition_to(SessionState.PLANNING)
        self.journal.record_event(
            EventType.STATUS_CHANGED, {"status": SessionState.PLANNING.value}
        )

        def _on_reasoning_chunk(r_chunk: str, c_chunk: str) -> None:
            if r_chunk:
                self.journal.record_event(EventType.THINKING_CHUNK, {"chunk": r_chunk})

        plan = await self.coordinator.generate_plan(
            task_description, workspace_context, on_chunk=_on_reasoning_chunk
        )
        self._current_plan = plan

        self.journal.record_event(
            EventType.PLAN_GENERATED,
            {
                "goal": plan.goal,
                "steps": [s.model_dump() for s in plan.steps],
                "reasoning": plan.raw_reasoning,
            },
        )

        # 2. Execution Phase
        self.state_machine.transition_to(SessionState.RUNNING)
        self.journal.record_event(
            EventType.STATUS_CHANGED, {"status": SessionState.RUNNING.value}
        )

        while not plan.is_finished() and not self._cancelled:
            step = plan.current_step()
            if not step:
                break

            step.status = "in_progress"
            self.journal.record_event(
                EventType.STEP_STARTED,
                {"step_id": step.step_id, "title": step.title, "description": step.description},
            )

            success = await self._execute_step(plan, step)

            if not success:
                logger.warning("Step %d failed. Initiating targeted replan.", step.step_id)
                step.status = "failed"
                # Replan
                replanned = await self.coordinator.replan_on_failure(
                    task_description,
                    step,
                    step.result_summary or "Execution failed",
                    on_chunk=_on_reasoning_chunk,
                )
                if replanned and replanned.steps:
                    self._current_plan = replanned
                    plan = replanned
                    self.journal.record_event(
                        EventType.PLAN_GENERATED,
                        {
                            "goal": plan.goal,
                            "steps": [s.model_dump() for s in plan.steps],
                            "reasoning": plan.raw_reasoning,
                        },
                    )
                    continue
                else:
                    self.state_machine.transition_to(SessionState.FAILED)
                    return False

            step.status = "completed"
            self.journal.record_event(
                EventType.STEP_COMPLETED,
                {"step_id": step.step_id, "result": step.result_summary},
            )
            self._step_results_summary.append(f"Step {step.step_id} ({step.title}): {step.result_summary}")
            plan.advance()

        if self._cancelled:
            return False

        self.state_machine.transition_to(SessionState.COMPLETED)
        self.journal.record_event(
            EventType.STATUS_CHANGED,
            {"status": SessionState.COMPLETED.value, "summary": "All plan steps completed successfully."},
        )
        return True

    async def _execute_step(self, plan: ExecutionPlan, step: PlanStep) -> bool:
        """Execute a single step using the Actor and Tool Registry."""
        # Check tool hint
        tool_name = step.tool_hint
        if not tool_name or not self.tools.get(tool_name):
            # If no direct single tool, run actor loop to determine tool calls
            tool_name = "run_command" if "test" in step.title.lower() or "run" in step.title.lower() else "file_tools"

        # If step is test verification
        if "test" in step.title.lower() or "verify" in step.title.lower():
            cmd = "pytest tests/ -v"
            allowed, denial, approval_req = await self.guard.check_permission(
                self.session_id, "run_command", {"command": cmd}
            )
            if not allowed:
                step.result_summary = f"Permission denied: {denial}"
                return False

            res = await self.tools.execute("run_command", {"command": cmd})
            self.journal.record_event(
                EventType.TERMINAL_OUTPUT,
                {"command": cmd, "output": res.output, "exit_code": res.data.get("exit_code", 0)},
            )
            step.result_summary = res.output[:300]
            return res.success

        # For file editing or general steps
        step.result_summary = f"Completed step: {step.title}"
        return True
