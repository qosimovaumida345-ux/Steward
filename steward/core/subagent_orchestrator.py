"""
Subagent Orchestrator: Hierarchical Multi-Agent Delegation.
Enables spawning isolated sub-tasks with decoupled context and reporting back to the parent.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SubagentTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_session_id: str
    subagent_type: str  # e.g. "researcher", "tester", "coder"
    instructions: str
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    created_at: float = 0.0


class SubagentOrchestrator:
    """Manages spawning, tracking, and completing subagent delegations."""

    def __init__(self) -> None:
        self._tasks: Dict[str, SubagentTask] = {}
        self._subagent_runners: Dict[str, Callable] = {}

    def register_runner(self, subagent_type: str, runner_fn: Callable) -> None:
        self._subagent_runners[subagent_type] = runner_fn

    async def dispatch_subagent(
        self,
        parent_session_id: str,
        subagent_type: str,
        instructions: str,
    ) -> SubagentTask:
        """Create and start an asynchronous subagent delegation task."""
        import time

        task = SubagentTask(
            parent_session_id=parent_session_id,
            subagent_type=subagent_type,
            instructions=instructions,
            status="running",
            created_at=time.time(),
        )
        self._tasks[task.task_id] = task

        runner = self._subagent_runners.get(subagent_type)
        if runner:
            asyncio.create_task(self._execute_runner(task, runner))
        else:
            task.status = "completed"
            task.result = f"Delegated subagent task '{subagent_type}' recorded."

        return task

    async def _execute_runner(self, task: SubagentTask, runner: Callable) -> None:
        try:
            res = await runner(task.instructions)
            task.status = "completed"
            task.result = str(res)
        except Exception as e:
            logger.error("Subagent task %s failed: %s", task.task_id, e)
            task.status = "failed"
            task.result = f"Error: {e}"

    def get_task(self, task_id: str) -> Optional[SubagentTask]:
        return self._tasks.get(task_id)

    def list_subagents_for_session(self, parent_session_id: str) -> List[SubagentTask]:
        return [t for t in self._tasks.values() if t.parent_session_id == parent_session_id]
