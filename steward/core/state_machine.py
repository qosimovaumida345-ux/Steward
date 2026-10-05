"""
Session State Machine and Lifecycle Transitions.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Set
from ..config.constants import SessionState

logger = logging.getLogger(__name__)

AgentState = SessionState


class StateTransitionError(Exception):
    pass


class SessionStateMachine:
    """Manages legal lifecycle state transitions for an autonomous agent session."""

    VALID_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
        AgentState.IDLE: {AgentState.PLANNING, AgentState.RUNNING, AgentState.TERMINATED},
        AgentState.PLANNING: {AgentState.RUNNING, AgentState.FAILED, AgentState.TERMINATED},
        AgentState.RUNNING: {
            AgentState.WAITING_APPROVAL,
            AgentState.PAUSED,
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.TERMINATED,
        },
        AgentState.WAITING_APPROVAL: {
            AgentState.RUNNING,
            AgentState.PAUSED,
            AgentState.TERMINATED,
            AgentState.FAILED,
        },
        AgentState.PAUSED: {AgentState.RUNNING, AgentState.TERMINATED},
        AgentState.COMPLETED: {AgentState.IDLE, AgentState.RUNNING},
        AgentState.FAILED: {AgentState.IDLE, AgentState.RUNNING},
        AgentState.TERMINATED: {AgentState.IDLE},
    }

    def __init__(self, initial_state: AgentState = AgentState.IDLE) -> None:
        self.state = initial_state
        self._listeners: List[Callable[[AgentState, AgentState], None]] = []

    def add_listener(self, callback: Callable[[AgentState, AgentState], None]) -> None:
        self._listeners.append(callback)

    def transition_to(self, new_state: AgentState) -> None:
        if new_state == self.state:
            return

        allowed = self.VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise StateTransitionError(
                f"Illegal state transition from {self.state.value} to {new_state.value}."
            )

        old_state = self.state
        self.state = new_state
        logger.info("Session state changed: %s -> %s", old_state.value, new_state.value)

        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                logger.error("Error in state transition listener: %s", e)
