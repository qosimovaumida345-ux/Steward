"""
Cryptographic Approval Token Manager.
Coordinates interactive permission requests and approval resolution.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ApprovalRequest(BaseModel):
    token: str = Field(default_factory=lambda: secrets.token_hex(8))
    session_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reason: str
    status: str = "pending"  # pending, approved, rejected, expired
    created_at: float = Field(default_factory=time.time)


class ApprovalManager:
    """Manages pending security approval requests."""

    def __init__(self) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}
        self._futures: Dict[str, asyncio.Future[bool]] = {}

    def create_request(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str,
    ) -> Tuple[ApprovalRequest, asyncio.Future[bool]]:
        req = ApprovalRequest(
            session_id=session_id,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()

        self._requests[req.token] = req
        self._futures[req.token] = future
        return req, future

    def resolve_request(self, token: str, approved: bool) -> bool:
        """Resolve a pending approval token."""
        req = self._requests.get(token)
        if not req or req.status != "pending":
            return False

        req.status = "approved" if approved else "rejected"
        fut = self._futures.pop(token, None)
        if fut and not fut.done():
            fut.set_result(approved)
        return True

    def get_pending_requests(self, session_id: Optional[str] = None) -> List[ApprovalRequest]:
        pending = [r for r in self._requests.values() if r.status == "pending"]
        if session_id:
            pending = [r for r in pending if r.session_id == session_id]
        return pending
