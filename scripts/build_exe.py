"""
Packaging Script: Compiles Steward binaries using PyInstaller.
Outputs: dist/agent_daemon.exe and dist/agent_app.exe
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT_DIR / "scripts" / "STEWARD.spec"


def build():
    print(f"Building Steward executables via PyInstaller...")
    print(f"Spec file: {SPEC_FILE}")
    print(f"Working directory: {ROOT_DIR}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode == 0:
        print("\nBuild completed successfully!")
        print(f"Outputs located in: {ROOT_DIR / 'dist'}")
    else:
        print(f"\nBuild failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
