"""
Permission Guard: Autonomous / Guarded / Sandboxed Policy Enforcer.
Validates tool executions, checks workspace containment, and gates sensitive actions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..config.constants import PermissionMode
from ..config.settings import get_settings
from .approval_manager import ApprovalManager, ApprovalRequest
from .command_heuristics import CommandHeuristics, SecurityRiskLevel

logger = logging.getLogger(__name__)


class PermissionGuard:
    """Enforces access control policies across agent tool execution."""

    READ_ONLY_TOOLS = {
        "view_file",
        "list_dir",
        "grep_search",
        "find_by_name",
        "capture_screen",
        "inspect_windows",
        "winrt_ocr",
    }

    def __init__(
        self,
        mode: Optional[PermissionMode] = None,
        workspace_root: Optional[Path] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ) -> None:
        settings = get_settings()
        self.mode = mode or settings.permission_mode
        self.workspace_root = workspace_root or settings.workspace_root
        self.heuristics = CommandHeuristics()
        self.approval_mgr = approval_manager or ApprovalManager()

    async def check_permission(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], Optional[ApprovalRequest]]:
        """
        Verify if tool execution is permitted under current policy.
        Returns:
            (is_allowed, denial_reason, approval_request_if_pending)
        """
        # 1. Sandboxed Mode: Strict read-only
        if self.mode == PermissionMode.SANDBOXED:
            if tool_name not in self.READ_ONLY_TOOLS:
                return (
                    False,
                    f"Action '{tool_name}' blocked: Sandboxed mode prohibits write or execution tools.",
                    None,
                )
            return True, None, None

        # 2. Check File Path Containment for file tools
        if tool_name in {"write_to_file", "replace_file_content", "view_file"}:
            path_arg = arguments.get("path")
            if path_arg and not self.heuristics.is_path_contained(path_arg, self.workspace_root):
                reason = f"Path '{path_arg}' attempts to access outside workspace root '{self.workspace_root}'."
                if self.mode == PermissionMode.GUARDED:
                    req, fut = self.approval_mgr.create_request(session_id, tool_name, arguments, reason)
                    return False, reason, req
                else:
                    return False, f"Permission Denied: {reason}", None

        # 3. Check Terminal Commands
        if tool_name == "run_command":
            cmd = arguments.get("command", "")
            risk_level, risk_desc = self.heuristics.assess_command_risk(cmd)

            if risk_level == SecurityRiskLevel.CRITICAL:
                return False, f"BLOCKED: {risk_desc}", None

            if risk_level in {SecurityRiskLevel.HIGH, SecurityRiskLevel.MODERATE}:
                if self.mode == PermissionMode.GUARDED:
                    req, fut = self.approval_mgr.create_request(
                        session_id, tool_name, arguments, risk_desc
                    )
                    return False, risk_desc, req

        # 4. Check Computer Use Input Synthesis
        if tool_name in {"mouse_click", "type_text"}:
            if self.mode == PermissionMode.GUARDED:
                reason = f"Direct hardware input synthesis requested ({tool_name})"
                req, fut = self.approval_mgr.create_request(session_id, tool_name, arguments, reason)
                return False, reason, req

        # Permitted
        return True, None, None
