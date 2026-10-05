"""
Unit tests for Terminal Execution and Win32 Job Object Tree Kill.
"""

import sys
import pytest
from steward.tools.terminal_tools import RunCommandTool, WindowsJobManager


def test_windows_job_manager_lifecycle():
    manager = WindowsJobManager(name="TestJob")
    # Verify handle created on Windows
    if sys.platform == "win32":
        assert manager.h_job is not None
    manager.close()


@pytest.mark.asyncio
async def test_run_command_powershell_success():
    tool = RunCommandTool()
    res = await tool.execute(command="Write-Output 'JobObjects_Test_Passed'")
    assert res.success is True
    assert "JobObjects_Test_Passed" in res.output
    assert res.data.get("exit_code") == 0


@pytest.mark.asyncio
async def test_run_command_timeout_kills_tree():
    tool = RunCommandTool()
    # Execute command that sleeps longer than timeout
    res = await tool.execute(command="Start-Sleep -Seconds 10", timeout_seconds=1.0)
    assert res.success is False
    assert res.data.get("timed_out") is True
    assert "timed out" in res.output.lower()
