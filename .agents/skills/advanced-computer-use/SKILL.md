---
name: advanced-computer-use
description: >-
  Enterprise-grade Computer Use & Desktop Automation Skill based on OpenAI CUA and
  Anthropic Computer Use standards. Operates Windows desktop via Desktop_Control MCP
  and Python automation scripts (pyautogui, mss, Win32 API, OCR, template matching).
  Covers high-DPI coordinate scaling, interactive desktop attachment, OCR centroid
  clicking, resilient Perception-Action-Verification (PAV) loops, and multi-monitor setups.
---

# Advanced Computer Use & Desktop Automation Skill

> **STANDARD**: Implements production-grade Windows OS automation combining vision, OCR,
> coordinate translation, mouse/keyboard manipulation, and state verification. Mirrors the
> architectural principles of OpenAI Computer-Using Agent (CUA) and Anthropic Computer Use API.

---

## 1. Core Operating Architecture

Windows desktop automation operates in two parallel execution modes:
1. **MCP Tool Orchestration**: Using the system's `Desktop_Control` MCP tools (`desktop_screenshot`, `desktop_ocr`, `desktop_mouse_click`, `desktop_keyboard_type`, etc.).
2. **Native Python Scripting**: Running standalone Python scripts leveraging `pyautogui`, `mss`, `PIL`, `pyperclip`, and `ctypes` with Win32 API handles.

### The Win32 Interactive Desktop Attachment Mandate
In sandboxed, service, or agentic environments, scripts often run inside an isolated window station (e.g. `exebox-*` or `Session 0`). To interact with the visible user desktop, all scripts must attach to the `Default` interactive desktop using 64-bit pointer-safe ctypes definitions:

```python
import ctypes

user32 = ctypes.windll.user32
user32.OpenDesktopW.restype = ctypes.c_void_p
user32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
user32.SetThreadDesktop.restype = ctypes.c_bool

def attach_interactive_desktop():
    """Switches the current thread to the user's visible 'Default' desktop station."""
    try:
        # GENERIC_ALL = 0x01FF
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            success = user32.SetThreadDesktop(hdesk)
            return bool(success)
    except Exception as e:
        print(f"Desktop switch warning: {e}")
    return False

attach_interactive_desktop()
```

---

## 2. Coordinate Geometry & DPI Normalization

Windows displays frequently use DPI scaling (125%, 150%, 175%, 200%). Uncalibrated clicks will miss targets because logical coordinates differ from physical hardware pixels.

### Normalization Mathematical Models
When interacting with AI vision models that predict normalized coordinates on a $[0, 1000] \times [0, 1000]$ bounding box:

$$X_{\text{screen}} = \text{round}\left( \frac{X_{\text{norm}}}{1000} \times \text{ScreenWidth} \right)$$
$$Y_{\text{screen}} = \text{round}\left( \frac{Y_{\text{norm}}}{1000} \times \text{ScreenHeight} \right)$$

### DPI-Aware Python Initialization
```python
import ctypes

def set_dpi_awareness():
    """Forces Windows process to report true physical pixel coordinates."""
    try:
        # Per-monitor DPI awareness (Windows 10 / 11)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

set_dpi_awareness()
```

---

## 3. The PAV (Perception-Action-Verification) Loop

Never perform "blind" clicks. Every autonomous action MUST execute through the 4-stage PAV cycle:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. PERCEIVE │ ──> │  2. LOCATE   │ ──> │   3. ACT     │ ──> │  4. VERIFY   │
│  Screenshot  │     │ OCR/Template │     │ Click / Type │     │ State Check  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       ▲                                                              │
       └───────────────────────── [Retry / Adjust] ───────────────────┘
```

1. **Perceive**: Capture current desktop state (`desktop_screenshot`).
2. **Locate**:
   - Primary: Match UI element by text using Windows OCR (`desktop_ocr`).
   - Secondary: Match graphical icon / button using OpenCV template matching (`desktop_find_on_screen`).
   - Fallback: Normalized coordinate estimation from visual prompt.
3. **Act**:
   - Move mouse with realistic acceleration curve.
   - Click centroid $(x + w/2, y + h/2)$.
   - Type keystrokes with natural micro-delays (20ms–50ms).
4. **Verify**:
   - Sleep 150ms–350ms to allow OS render cycle to paint updates.
   - Inspect screen to ensure intended state change occurred (modal appeared, input focused, text appeared).
   - If change not detected, retry with alternate coordinate offset or keyboard navigation (e.g. `Tab`, `Enter`).

---

## 4. MCP Desktop_Control Tool Reference

| Tool | Parameters | Purpose |
|---|---|---|
| `desktop_screenshot` | `{ filepath?, region?, monitor?, scale? }` | Captures crisp PNG screenshot. |
| `desktop_ocr` | `{ region?, language? }` | Extracts all on-screen text with bounding boxes. |
| `desktop_find_on_screen` | `{ template_path, threshold?, region? }` | Finds PNG template occurrences on screen. |
| `desktop_mouse_click` | `{ x, y, button?, clicks? }` | Clicks at exact screen coordinates. |
| `desktop_mouse_move` | `{ x, y, duration? }` | Smooth mouse glide to coordinate. |
| `desktop_mouse_drag` | `{ start_x, start_y, end_x, end_y, duration? }` | Performs drag and drop gesture. |
| `desktop_mouse_scroll`| `{ clicks, direction? }` | Scrolls wheel up/down/left/right. |
| `desktop_keyboard_type`| `{ text, interval? }` | Types string into active focused control. |
| `desktop_keyboard_press`| `{ key, presses? }` | Presses special keys (`enter`, `esc`, `tab`, `backspace`). |
| `desktop_keyboard_hotkey`| `{ keys: ["ctrl", "c"] }` | Executes keyboard combination shortcuts. |
| `desktop_list_windows` | `{}` | Lists all visible top-level windows with HWND and title. |
| `desktop_focus_window` | `{ query?, hwnd? }` | Brings specified window to front and activates focus. |
| `desktop_clipboard_read`| `{}` | Reads text contents from clipboard. |
| `desktop_clipboard_write`| `{ text }` | Writes text to clipboard for instant pasting. |
| `desktop_wait` | `{ seconds }` | Non-blocking sleep for animations / loading. |

---

## 5. Production Python Automation Engine (`desktop_agent_kit.py`)

Here is the complete, self-contained Python desktop automation engine that can be run directly or integrated into any agent workflow:

```python
#!/usr/bin/env python3
"""
Desktop Agent Kit: Standalone Vision & Automation Engine
Supports high-DPI scaling, interactive desktop attachment, OCR centroid clicking,
smooth Bezier mouse trajectories, and verification loops.
"""

from __future__ import annotations
import sys
import os
import time
import math
import random
import ctypes
import pyautogui
import pyperclip
import mss
from PIL import Image

# 1. Attach to Interactive Desktop & Enable High DPI
user32 = ctypes.windll.user32
user32.OpenDesktopW.restype = ctypes.c_void_p
user32.OpenDesktopW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]
user32.SetThreadDesktop.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.ShowWindow.restype = ctypes.c_bool
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.SetForegroundWindow.restype = ctypes.c_bool

try:
    hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
    if hdesk:
        user32.SetThreadDesktop(hdesk)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02


class DesktopAgent:
    def __init__(self):
        self.sct = mss.mss()
        self.screen_width, self.screen_height = pyautogui.size()

    def denormalize_coords(self, x_norm: float, y_norm: float) -> tuple[int, int]:
        """Converts [0, 1000] normalized model coordinates to physical pixels."""
        x = int(round((x_norm / 1000.0) * self.screen_width))
        y = int(round((y_norm / 1000.0) * self.screen_height))
        return (x, y)

    def screenshot(self, output_path: str = "screen.png") -> str:
        """Captures full screen or primary monitor to disk."""
        monitor = self.sct.monitors[1]
        img = self.sct.grab(monitor)
        mss.tools.to_png(img.rgb, img.size, output=output_path)
        return os.path.abspath(output_path)

    def human_move(self, target_x: int, target_y: int, steps: int = 15):
        """Moves cursor along a smooth curved path to emulate human motion."""
        start_x, start_y = pyautogui.position()
        for i in range(1, steps + 1):
            t = i / float(steps)
            # Smooth ease-in-out curve
            ease_t = 3 * (t ** 2) - 2 * (t ** 3)
            # Subtle random deviation
            jitter_x = random.randint(-1, 1) if i < steps else 0
            jitter_y = random.randint(-1, 1) if i < steps else 0
            curr_x = int(start_x + (target_x - start_x) * ease_t + jitter_x)
            curr_y = int(start_y + (target_y - start_y) * ease_t + jitter_y)
            pyautogui.moveTo(curr_x, curr_y)
            time.sleep(0.01)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """Human-like move followed by click."""
        self.human_move(x, y)
        time.sleep(0.05)
        pyautogui.click(x, y, button=button, clicks=clicks)

    def click_box(self, x: int, y: int, w: int, h: int, button: str = "left"):
        """Clicks the exact center of a bounding box."""
        cx = x + (w // 2)
        cy = y + (h // 2)
        self.click(cx, cy, button=button)

    def type_text(self, text: str, use_clipboard: bool = False):
        """Types text cleanly. Uses clipboard for large text or special unicode."""
        if use_clipboard or len(text) > 30:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)
        else:
            for char in text:
                pyautogui.write(char)
                time.sleep(random.uniform(0.015, 0.045))

    def focus_window(self, title_substring: str) -> bool:
        """Brings a window with matching title to the foreground."""
        found_hwnd = None

        def enum_handler(hwnd, extra):
            nonlocal found_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if title_substring.lower() in buff.value.lower():
                        found_hwnd = hwnd
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(EnumWindowsProc(enum_handler), 0)

        if found_hwnd:
            user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
            user32.SetForegroundWindow(found_hwnd)
            time.sleep(0.2)
            return True
        return False

    def pav_action(self, target_finder_fn, action_fn, verifier_fn, max_retries: int = 3) -> bool:
        """
        Executes the full Perception-Action-Verification loop.
        """
        for attempt in range(1, max_retries + 1):
            # 1. Perceive & Locate
            coords = target_finder_fn(self)
            if not coords:
                print(f"[PAV] Attempt {attempt}: Target not found, retrying...")
                time.sleep(0.5)
                continue

            target_x, target_y = coords
            print(f"[PAV] Attempt {attempt}: Located target at ({target_x}, {target_y})")

            # 2. Act
            action_fn(self, target_x, target_y)

            # 3. Verification delay
            time.sleep(0.3)

            # 4. Verify
            if verifier_fn(self):
                print(f"[PAV] Attempt {attempt}: Verification succeeded!")
                return True
            else:
                print(f"[PAV] Attempt {attempt}: Verification check failed.")

        return False


if __name__ == "__main__":
    agent = DesktopAgent()
    print(f"Screen resolution: {agent.screen_width}x{agent.screen_height}")
    shot = agent.screenshot("current_desktop.png")
    print(f"Captured screenshot to: {shot}")
```

---

## 6. Practical Automation Workflows

### Scenario 1: Launching an Application & Opening a File
```python
agent = DesktopAgent()
# 1. Press Win Key
pyautogui.press("win")
time.sleep(0.2)
# 2. Type App Name
agent.type_text("Roblox Studio")
time.sleep(0.3)
# 3. Press Enter
pyautogui.press("enter")
time.sleep(3.0)
# 4. Focus window
agent.focus_window("Roblox Studio")
```

### Scenario 2: Clicking a Button via OCR Centroid
1. Call `desktop_ocr(region=...)`.
2. Find the bounding box matching the desired text label (e.g. `"Publish to Roblox"` or `"Sign In"`).
3. Compute center: $X_c = X + \lfloor W/2 \rfloor$, $Y_c = Y + \lfloor H/2 \rfloor$.
4. Call `desktop_mouse_click(x=Xc, y=Yc)`.
5. Verify resulting modal or state change via screenshot.
