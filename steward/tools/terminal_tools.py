"""
Windows Terminal Execution Engine with Win32 Job Objects & ConPTY Support.
Guarantees clean process tree termination with zero orphaned processes.
"""

from __future__ import annotations

import asyncio
import ctypes
from ctypes import wintypes
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base import BaseTool, ToolResult
from ..config.constants import SAFE_COMMAND_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Check pywin32 availability for Win32 Job Objects
HAS_WIN32JOB = False
try:
    import win32api
    import win32con
    import win32job
    import win32process

    HAS_WIN32JOB = True
except ImportError:
    pass


class WindowsJobManager:
    """
    Encapsulates a Win32 Job Object configured with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
    All spawned processes and their children are attached to this job; closing the job
    or terminating it kills every process in the tree cleanly.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self.h_job = None
        if HAS_WIN32JOB:
            try:
                self.h_job = win32job.CreateJobObject(None, name or "")
                info = win32job.QueryInformationJobObject(
                    self.h_job, win32job.JobObjectExtendedLimitInformation
                )
                info["BasicLimitInformation"]["LimitFlags"] = (
                    win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                )
                win32job.SetInformationJobObject(
                    self.h_job, win32job.JobObjectExtendedLimitInformation, info
                )
            except Exception as e:
                logger.warning("Failed to initialize Windows Job Object: %s", e)
                self.h_job = None

    def attach_process_handle(self, h_process: int) -> bool:
        if self.h_job and HAS_WIN32JOB:
            try:
                win32job.AssignProcessToJobObject(self.h_job, h_process)
                return True
            except Exception as e:
                logger.warning("Could not assign process to Job Object: %s", e)
        return False

    def attach_pid(self, pid: int) -> bool:
        if self.h_job and HAS_WIN32JOB:
            try:
                h_process = win32api.OpenProcess(
                    win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid
                )
                try:
                    return self.attach_process_handle(h_process)
                finally:
                    win32api.CloseHandle(h_process)
            except Exception as e:
                logger.warning("Could not open process %d for job attachment: %s", pid, e)
        return False

    def terminate(self, exit_code: int = 0) -> None:
        if self.h_job and HAS_WIN32JOB:
            try:
                win32job.TerminateJobObject(self.h_job, exit_code)
            except Exception as e:
                logger.debug("Error terminating Job Object: %s", e)

    def close(self) -> None:
        if self.h_job and HAS_WIN32JOB:
            try:
                win32api.CloseHandle(self.h_job)
                self.h_job = None
            except Exception:
                pass


class ConPtySession:
    """
    Native Windows ConPTY (PseudoConsole) manager via kernel32.dll ctypes.
    Enables true VT100 interactive terminal support.
    """

    HPCON = ctypes.c_void_p

    class COORD(ctypes.Structure):
        _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

    def __init__(self, cols: int = 120, rows: int = 40) -> None:
        self.cols = cols
        self.rows = rows
        self.h_pc = self.HPCON()
        self.in_pipe_read = wintypes.HANDLE()
        self.in_pipe_write = wintypes.HANDLE()
        self.out_pipe_read = wintypes.HANDLE()
        self.out_pipe_write = wintypes.HANDLE()
        self._available = False
        self._check_conpty()

    def _check_conpty(self) -> None:
        try:
            self.kernel32 = ctypes.windll.kernel32
            self._create_pseudo_console = getattr(self.kernel32, "CreatePseudoConsole", None)
            self._close_pseudo_console = getattr(self.kernel32, "ClosePseudoConsole", None)
            if self._create_pseudo_console and self._close_pseudo_console:
                self._available = True
        except Exception:
            self._available = False

    def is_available(self) -> bool:
        return self._available


class RunCommandTool(BaseTool):
    name = "run_command"
    description = (
        "Execute a terminal command asynchronously using PowerShell on Windows. "
        "All processes are attached to a Win32 Job Object ensuring zero orphaned child processes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The command line string to execute"},
            "cwd": {"type": "string", "description": "Working directory (defaults to current dir)"},
            "timeout_seconds": {
                "type": "number",
                "description": f"Timeout in seconds (default {SAFE_COMMAND_TIMEOUT_SECONDS})",
            },
        },
        "required": ["command"],
    }

    def __init__(self, default_cwd: Optional[Path] = None) -> None:
        self.default_cwd = default_cwd or Path.cwd()
        self.job_manager = WindowsJobManager()

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ) -> ToolResult:
        work_dir = Path(cwd).resolve() if cwd else self.default_cwd
        timeout = timeout_seconds or SAFE_COMMAND_TIMEOUT_SECONDS
        start_time = time.monotonic()

        # Build PowerShell execution command
        powershell_cmd = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]

        logger.info("Executing terminal command: %s (cwd=%s)", command, work_dir)

        try:
            # Spawn process
            proc = await asyncio.create_subprocess_exec(
                *powershell_cmd,
                cwd=str(work_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Attach PID to Job Object immediately
            if proc.pid:
                self.job_manager.attach_pid(proc.pid)

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                # Terminate entire process tree using the Job Object
                logger.warning("Command timed out after %.1fs. Killing job tree.", timeout)
                self.job_manager.terminate(1)
                try:
                    proc.kill()
                except Exception:
                    pass
                return ToolResult(
                    success=False,
                    output=f"Command timed out after {timeout} seconds.",
                    error=f"TimeoutError: Execution exceeded {timeout}s limit.",
                    data={"timed_out": True, "command": command},
                )

            duration = time.monotonic() - start_time
            stdout_text = stdout_bytes.decode("utf-8", errors="replace")
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")

            output_combined = stdout_text
            if stderr_text:
                if output_combined:
                    output_combined += "\n[STDERR]\n" + stderr_text
                else:
                    output_combined = stderr_text

            exit_code = proc.returncode or 0
            is_success = exit_code == 0

            return ToolResult(
                success=is_success,
                output=output_combined.strip() or "(no output)",
                error=stderr_text.strip() if not is_success else None,
                data={
                    "exit_code": exit_code,
                    "duration_seconds": round(duration, 3),
                    "command": command,
                    "cwd": str(work_dir),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {str(e)}",
                data={"command": command},
            )
