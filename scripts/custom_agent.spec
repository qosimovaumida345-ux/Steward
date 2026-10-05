# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Multi-Binary Spec: agent_daemon.exe and agent_app.exe

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Hidden imports for daemon
daemon_hidden = collect_submodules('STEWARD') + [
    'aiohttp', 'websockets', 'httpx', 'psycopg2', 'pg8000', 'pydantic', 'win32job', 'mss', 'PIL'
]

# Hidden imports for desktop GUI
ui_hidden = daemon_hidden + [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'qtpy'
]

# 1. Daemon Executable Analysis
a_daemon = Analysis(
    ['../run_daemon.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=daemon_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'qtpy', 'matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_daemon = PYZ(a_daemon.pure, a_daemon.zipped_data, cipher=block_cipher)

exe_daemon = EXE(
    pyz_daemon,
    a_daemon.scripts,
    a_daemon.binaries,
    a_daemon.zipfiles,
    a_daemon.datas,
    [],
    name='agent_daemon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 2. Desktop GUI Executable Analysis
a_app = Analysis(
    ['../run_app.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=ui_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_app = PYZ(a_app.pure, a_app.zipped_data, cipher=block_cipher)

exe_app = EXE(
    pyz_app,
    a_app.scripts,
    a_app.binaries,
    a_app.zipfiles,
    a_app.datas,
    [],
    name='agent_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
