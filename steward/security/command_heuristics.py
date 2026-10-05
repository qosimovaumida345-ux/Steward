"""
Command Heuristics and PowerShell Alias Canonicalization.
Analyzes AST tokens and regex patterns to identify destructive commands and path escapes.
"""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SecurityRiskLevel(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CommandHeuristics:
    """
    Canonicalizes PowerShell command aliases and detects destructive command patterns.
    """

    POWERSHELL_ALIASES: Dict[str, str] = {
        "ri": "Remove-Item",
        "rm": "Remove-Item",
        "del": "Remove-Item",
        "erase": "Remove-Item",
        "rd": "Remove-Item",
        "rmdir": "Remove-Item",
        "kill": "Stop-Process",
        "sc": "Set-Content",
        "gc": "Get-Content",
        "cat": "Get-Content",
        "type": "Get-Content",
        "ls": "Get-ChildItem",
        "dir": "Get-ChildItem",
        "gci": "Get-ChildItem",
        "cp": "Copy-Item",
        "copy": "Copy-Item",
        "cpi": "Copy-Item",
        "mv": "Move-Item",
        "move": "Move-Item",
        "mi": "Move-Item",
        "ps": "Get-Process",
        "gps": "Get-Process",
        "curl": "Invoke-WebRequest",
        "wget": "Invoke-WebRequest",
        "irm": "Invoke-RestMethod",
        "iwr": "Invoke-WebRequest",
    }

    CATASTROPHIC_PATTERNS: List[re.Pattern] = [
        re.compile(r"\bformat\s+[a-z]:", re.I),
        re.compile(r"\bdiskpart\b", re.I),
        re.compile(r"\breg\s+delete\b", re.I),
        re.compile(r"\bbcdedit\b", re.I),
        re.compile(r"\bvssadmin\s+delete\b", re.I),
        re.compile(r"Remove-Item\s+.*-(?:Recurse|r)\s+.*[a-zA-Z]:\\(?:\s|$)", re.I),
        re.compile(r"rmdir\s+/(?:s|S)\s+/(?:q|Q)\s+[a-zA-Z]:\\", re.I),
        re.compile(r"\bgit\s+push\b.*(?:--force|-f)\b", re.I),
    ]

    MODERATE_PATTERNS: List[re.Pattern] = [
        re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
        re.compile(r"\bgit\s+clean\s+-f\b", re.I),
        re.compile(r"Remove-Item\b", re.I),
        re.compile(r"\brm\s+-rf\b", re.I),
        re.compile(r"\bpip\s+install\b", re.I),
        re.compile(r"\bnpm\s+install\b", re.I),
    ]

    def canonicalize_command(self, command: str) -> str:
        """Replace leading PowerShell aliases with their canonical cmdlet names."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return command
        cmd_name = parts[0].lower()
        if cmd_name in self.POWERSHELL_ALIASES:
            canonical = self.POWERSHELL_ALIASES[cmd_name]
            rest = parts[1] if len(parts) > 1 else ""
            return f"{canonical} {rest}".strip()
        return command

    def assess_command_risk(self, command: str) -> Tuple[SecurityRiskLevel, str]:
        """
        Evaluate risk level of a terminal command.
        Returns (RiskLevel, explanation).
        """
        canonical_cmd = self.canonicalize_command(command)

        # 1. Check catastrophic
        for pat in self.CATASTROPHIC_PATTERNS:
            if pat.search(canonical_cmd) or pat.search(command):
                return (
                    SecurityRiskLevel.CRITICAL,
                    f"Catastrophic system-level destructive command detected: {pat.pattern}",
                )

        # 2. Check moderate risk
        for pat in self.MODERATE_PATTERNS:
            if pat.search(canonical_cmd) or pat.search(command):
                return (
                    SecurityRiskLevel.HIGH,
                    f"Potentially destructive or system-modifying command: {pat.pattern}",
                )

        return SecurityRiskLevel.SAFE, "Command passes standard heuristic checks"

    def is_path_contained(self, target_path: str, workspace_root: Path) -> bool:
        """
        Verify that a target file path does not escape the active workspace.
        """
        try:
            resolved_target = Path(target_path).resolve()
            resolved_root = workspace_root.resolve()
            return resolved_target == resolved_root or resolved_root in resolved_target.parents
        except Exception:
            return False
