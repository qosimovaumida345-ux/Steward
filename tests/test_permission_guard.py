"""
Unit tests for Permission Guard, Command Heuristics, and PowerShell Alias Resolution.
"""

from pathlib import Path
import pytest
from steward.config.constants import PermissionMode
from steward.security.approval_manager import ApprovalManager
from steward.security.command_heuristics import CommandHeuristics, SecurityRiskLevel
from steward.security.permission_guard import PermissionGuard


def test_command_heuristics_alias_canonicalization():
    heuristics = CommandHeuristics()
    assert heuristics.canonicalize_command("ri foo.txt") == "Remove-Item foo.txt"
    assert heuristics.canonicalize_command("rm -rf node_modules") == "Remove-Item -rf node_modules"
    assert heuristics.canonicalize_command("kill 1234") == "Stop-Process 1234"
    assert heuristics.canonicalize_command("gci C:\\") == "Get-ChildItem C:\\"


def test_catastrophic_command_detection():
    heuristics = CommandHeuristics()
    # format
    risk, desc = heuristics.assess_command_risk("format c: /fs:NTFS")
    assert risk == SecurityRiskLevel.CRITICAL

    # diskpart
    risk, desc = heuristics.assess_command_risk("diskpart /s script.txt")
    assert risk == SecurityRiskLevel.CRITICAL

    # force push
    risk, desc = heuristics.assess_command_risk("git push origin main --force")
    assert risk == SecurityRiskLevel.CRITICAL


def test_workspace_containment(tmp_path: Path):
    heuristics = CommandHeuristics()
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()

    inside_file = ws_root / "src" / "app.py"
    assert heuristics.is_path_contained(str(inside_file), ws_root) is True

    outside_file = tmp_path / "other" / "secret.env"
    assert heuristics.is_path_contained(str(outside_file), ws_root) is False


@pytest.mark.asyncio
async def test_permission_guard_sandboxed_mode(tmp_path: Path):
    guard = PermissionGuard(mode=PermissionMode.SANDBOXED, workspace_root=tmp_path)

    # Read allowed
    allowed, _, _ = await guard.check_permission("s1", "view_file", {"path": "test.txt"})
    assert allowed is True

    # Write blocked
    allowed, denial, _ = await guard.check_permission("s1", "write_to_file", {"path": "test.txt"})
    assert allowed is False
    assert "Sandboxed" in denial


@pytest.mark.asyncio
async def test_permission_guard_guarded_mode_approvals(tmp_path: Path):
    approval_mgr = ApprovalManager()
    guard = PermissionGuard(
        mode=PermissionMode.GUARDED,
        workspace_root=tmp_path,
        approval_manager=approval_mgr,
    )

    # Destructive or moderate command triggers approval request
    cmd = "git reset --hard HEAD~1"
    allowed, reason, req = await guard.check_permission("s1", "run_command", {"command": cmd})
    assert allowed is False
    assert req is not None
    assert req.token in [r.token for r in approval_mgr.get_pending_requests()]

    # Resolve approval
    approval_mgr.resolve_request(req.token, approved=True)
    assert req.status == "approved"
