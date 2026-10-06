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
    """Production-grade desktop control agent with PAV loop support."""

    def __init__(self):
        mss_cls = getattr(mss, "MSS", mss.mss)
        self.sct = mss_cls()
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
            ease_t = 3 * (t ** 2) - 2 * (t ** 3)
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
            user32.ShowWindow(found_hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(found_hwnd)
            time.sleep(0.2)
            return True
        return False

    def pav_action(self, target_finder_fn, action_fn, verifier_fn, max_retries: int = 3) -> bool:
        """
        Executes the full Perception-Action-Verification loop.
        """
        for attempt in range(1, max_retries + 1):
            coords = target_finder_fn(self)
            if not coords:
                print(f"[PAV] Attempt {attempt}: Target not found, retrying...")
                time.sleep(0.5)
                continue

            target_x, target_y = coords
            print(f"[PAV] Attempt {attempt}: Located target at ({target_x}, {target_y})")
            action_fn(self, target_x, target_y)
            time.sleep(0.3)

            if verifier_fn(self):
                print(f"[PAV] Attempt {attempt}: Verification succeeded!")
                return True
            else:
                print(f"[PAV] Attempt {attempt}: Verification check failed.")

        return False


if __name__ == "__main__":
    agent = DesktopAgent()
    print(f"Screen resolution: {agent.screen_width}x{agent.screen_height}")
    print("DesktopAgent initialized successfully.")
