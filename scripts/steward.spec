# -*- mode: python ; coding: utf-8 -*-
# PyInstaller Multi-Binary Spec: steward_daemon.exe and steward_app.exe

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

SPEC_DIR = Path(SPECPATH)
ROOT_DIR = SPEC_DIR.parent

block_cipher = None

# Ensure root directory is on sys.path
sys.path.insert(0, str(ROOT_DIR))

# Hidden imports for daemon
daemon_hidden = collect_submodules('steward') + [
    'aiohttp', 'websockets', 'httpx', 'psycopg2', 'pg8000', 'pydantic',
    'win32job', 'win32process', 'win32api', 'win32con', 'mss', 'PIL', 'rich'
]

# Hidden imports for desktop GUI
ui_hidden = daemon_hidden + collect_submodules('PyQt6') + [
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'qtpy'
]

# Collect PyQt6 data files and dynamic libraries (platforms/qwindows.dll, styles, etc.)
pyqt6_datas = collect_data_files('PyQt6')
pyqt6_binaries = collect_dynamic_libs('PyQt6')

# Specifically duplicate qwindows.dll into root 'platforms' directory to guarantee discovery
extra_binaries = []
for src, dst in list(pyqt6_binaries) + list(pyqt6_datas):
    if 'qwindows.dll' in os.path.basename(str(src)).lower():
        extra_binaries.append((str(src), 'platforms'))

# Extra application data files
extra_datas = []
if (ROOT_DIR / '.env').exists():
    extra_datas.append((str(ROOT_DIR / '.env'), '.'))
if (ROOT_DIR / 'CustomAgentLogo.png').exists():
    extra_datas.append((str(ROOT_DIR / 'CustomAgentLogo.png'), '.'))

# 1. Daemon Executable Analysis
a_daemon = Analysis(
    [str(ROOT_DIR / 'run_daemon.py')],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=extra_datas,
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
    name='steward_daemon',
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
    [str(ROOT_DIR / 'run_app.py')],
    pathex=[str(ROOT_DIR)],
    binaries=pyqt6_binaries + extra_binaries,
    datas=pyqt6_datas + extra_datas,
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
    name='steward_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['qwindows.dll', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', '*PyQt6*'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
