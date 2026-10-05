"""
Windows Computer Use Engine.
Provides Per-Monitor DPI awareness, MSS DXGI screen capture, SendInput hardware synthesis,
native WinRT OCR, and UI window inspection.
"""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import io
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Set Per-Monitor DPI Awareness
try:
    # 2 = PROCESS_PER_MONITOR_DPI_AWARE_V2
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------- Windows SendInput Hardware Synthesis ----------------

ULONG_PTR = ctypes.c_ulong if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004


def send_mouse_click(x: int, y: int, button: str = "left") -> None:
    """Move cursor and click at absolute screen coordinates."""
    # Convert pixels to normalized absolute coordinates (0 to 65535)
    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)

    norm_x = int((x * 65535) / max(screen_w, 1))
    norm_y = int((y * 65535) / max(screen_h, 1))

    # Move
    inp_move = INPUT(
        type=INPUT_MOUSE,
        u=INPUT_UNION(
            mi=MOUSEINPUT(
                dx=norm_x,
                dy=norm_y,
                dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                mouseData=0,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )

    down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
    up_flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP

    inp_down = INPUT(
        type=INPUT_MOUSE,
        u=INPUT_UNION(
            mi=MOUSEINPUT(dx=norm_x, dy=norm_y, dwFlags=down_flag | MOUSEEVENTF_ABSOLUTE, mouseData=0, time=0, dwExtraInfo=0)
        ),
    )
    inp_up = INPUT(
        type=INPUT_MOUSE,
        u=INPUT_UNION(
            mi=MOUSEINPUT(dx=norm_x, dy=norm_y, dwFlags=up_flag | MOUSEEVENTF_ABSOLUTE, mouseData=0, time=0, dwExtraInfo=0)
        ),
    )

    inputs = (INPUT * 3)(inp_move, inp_down, inp_up)
    user32.SendInput(3, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def send_keystroke_text(text: str) -> None:
    """Send text characters via SendInput UNICODE packets."""
    user32 = ctypes.windll.user32
    for char in text:
        code = ord(char)
        down = INPUT(
            type=INPUT_KEYBOARD,
            u=INPUT_UNION(
                ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
            ),
        )
        up = INPUT(
            type=INPUT_KEYBOARD,
            u=INPUT_UNION(
                ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
            ),
        )
        inputs = (INPUT * 2)(down, up)
        user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        time.sleep(0.01)


# ---------------- Tools ----------------

class CaptureScreenTool(BaseTool):
    name = "capture_screen"
    description = "Capture desktop screenshot using high-speed MSS DirectX capture."
    parameters = {
        "type": "object",
        "properties": {
            "monitor_index": {"type": "integer", "description": "Monitor index (1=primary, default 1)"},
            "save_path": {"type": "string", "description": "Optional file path to save image"},
        },
    }

    async def execute(
        self, monitor_index: int = 1, save_path: Optional[str] = None, **kwargs
    ) -> ToolResult:
        try:
            import mss
            from PIL import Image

            # Use MSS
            try:
                sct = mss.MSS()
            except AttributeError:
                sct = mss.mss()

            with sct:
                monitors = sct.monitors
                idx = monitor_index if 0 < monitor_index < len(monitors) else 1
                mon = monitors[idx]
                sct_img = sct.grab(mon)

                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                # If save path specified, save to disk
                if save_path:
                    out_path = Path(save_path).resolve()
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    img.save(out_path, format="PNG")
                    return ToolResult(
                        success=True,
                        output=f"Screenshot saved to {out_path} ({img.width}x{img.height})",
                        data={"width": img.width, "height": img.height, "path": str(out_path)},
                    )

                # Otherwise encode to base64
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                return ToolResult(
                    success=True,
                    output=f"Screen captured: {img.width}x{img.height} (Monitor {idx})",
                    data={"width": img.width, "height": img.height, "base64_png": b64[:200] + "..."},
                )
        except Exception as e:
            return ToolResult(success=False, error=f"Screen capture failed: {e}")


class MouseClickTool(BaseTool):
    name = "mouse_click"
    description = "Synthesize hardware mouse click at specified screen pixel coordinates."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X pixel coordinate"},
            "y": {"type": "integer", "description": "Y pixel coordinate"},
            "button": {"type": "string", "enum": ["left", "right"], "description": "Mouse button"},
        },
        "required": ["x", "y"],
    }

    async def execute(self, x: int, y: int, button: str = "left", **kwargs) -> ToolResult:
        try:
            send_mouse_click(x, y, button=button)
            return ToolResult(
                success=True,
                output=f"Sent {button} click to ({x}, {y})",
                data={"x": x, "y": y, "button": button},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Mouse click failed: {e}")


class TypeTextTool(BaseTool):
    name = "type_text"
    description = "Synthesize hardware keyboard typing for a string of text."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text content to type into active control"},
        },
        "required": ["text"],
    }

    async def execute(self, text: str, **kwargs) -> ToolResult:
        try:
            send_keystroke_text(text)
            return ToolResult(
                success=True,
                output=f"Typed {len(text)} characters into active window.",
                data={"length": len(text)},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Typing text failed: {e}")


class InspectWindowsTool(BaseTool):
    name = "inspect_windows"
    description = "Enumerate visible top-level Windows application windows and their bounding boxes."
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        try:
            import win32gui

            windows = []

            def _enum_callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    if title:
                        rect = win32gui.GetWindowRect(hwnd)
                        w = rect[2] - rect[0]
                        h = rect[3] - rect[1]
                        if w > 50 and h > 50:
                            extra.append({
                                "hwnd": hwnd,
                                "title": title,
                                "left": rect[0],
                                "top": rect[1],
                                "width": w,
                                "height": h,
                            })

            win32gui.EnumWindows(_enum_callback, windows)

            formatted = [
                f"[HWND {w['hwnd']}] '{w['title']}' ({w['width']}x{w['height']} at {w['left']},{w['top']})"
                for w in windows
            ]

            return ToolResult(
                success=True,
                output=f"Found {len(windows)} visible windows:\n" + "\n".join(formatted[:30]),
                data={"windows": windows},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Window enumeration failed: {e}")


class WinRtOcrTool(BaseTool):
    name = "winrt_ocr"
    description = "Run native Windows OCR on a screenshot file to extract visible text."
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Path to image file for OCR"},
        },
        "required": ["image_path"],
    }

    async def execute(self, image_path: str, **kwargs) -> ToolResult:
        p = Path(image_path).resolve()
        if not p.exists():
            return ToolResult(success=False, error=f"Image not found: {p}")

        # PowerShell script using Windows.Media.Ocr
        ps_script = f"""
        Add-Type -AssemblyName System.Drawing
        [Windows.Globalization.Language, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
        [Windows.Media.Ocr.OcrEngine, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null
        [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation.UniversalApiContract, ContentType = WindowsRuntime] | Out-Null

        $path = "{str(p).replace('\\', '\\\\')}"
        $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync($path).GetAwaiter().GetResult()
        $stream = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read).GetAwaiter().GetResult()
        $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).GetAwaiter().GetResult()
        $bitmap = $decoder.GetSoftwareBitmapAsync().GetAwaiter().GetResult()

        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if (-not $engine) {{ $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('en-US')) }}

        $result = $engine.RecognizeAsync($bitmap).GetAwaiter().GetResult()
        $result.Text
        """

        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            text_out = res.stdout.strip()
            if text_out:
                return ToolResult(
                    success=True,
                    output=f"WinRT OCR Extracted Text:\n{text_out}",
                    data={"text": text_out},
                )
            else:
                return ToolResult(
                    success=True,
                    output="OCR completed; no text was detected on the image.",
                    data={"text": ""},
                )
        except Exception as e:
            return ToolResult(success=False, error=f"WinRT OCR execution failed: {e}")
