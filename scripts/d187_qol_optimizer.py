#!/usr/bin/env python3
"""
District 187: Sin Streets — Windows 11 QoL & Engine Optimizer
=============================================================
Provides:
  1. Borderless Windowed Fullscreen enforcer via Win32 user32 API (instant Alt+Tab).
  2. Raw Mouse Input (zero smoothing/acceleration) & Competitive FOV Unlocker (90-110).
  3. Native Archive Mounter (mounts HD1..HD6 + CustomMod_PTBR.Res00 in Default.archcfg).
"""

import argparse
import ctypes
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.join(BASE_DIR, "targets", "district-187", "client-rebirth")
AUTOEXEC_PATH = os.path.join(CLIENT_DIR, "autoexec.cfg")
SETTINGS_PATH = os.path.join(CLIENT_DIR, "settings.cfg")
ARCHCFG_PATH = os.path.join(CLIENT_DIR, "Default.archcfg")

# Win32 Constants for Borderless Windowed Mode
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0004


def get_primary_monitor_resolution() -> tuple:
    if os.name == "nt":
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
    return 1920, 1080


def apply_qol_profile(
    fov: int = 95,
    raw_mouse: bool = True,
    borderless: bool = True,
    max_fps: int = 0,
    enable_ptbr_mod: bool = True,
) -> dict:
    """Writes optimized autoexec.cfg and updates Default.archcfg."""
    screen_w, screen_h = get_primary_monitor_resolution()
    fov = max(75, min(115, int(fov)))

    lines = [
        "// District 187: Sin Streets — Windows 11 Competitive & QoL Profile",
        f"MaxFPS {max_fps}",
        f"Fov {fov}",
        f"FovY {round(fov * 0.75, 1)}",
        "BindTexturesMipOffset 0",
        "GraphicQualityLevel 3",
        "ShowFrameRate 1",
        "VSyncOnFlip 0",
        f"Windowed {1 if borderless else 0}",
        f"ScreenWidth {screen_w}",
        f"ScreenHeight {screen_h}",
        "BitDepth 32",
    ]
    if raw_mouse:
        lines.extend([
            "MouseSmoothing 0",
            "MouseFilter 0",
            "UseRawMouseInput 1",
            "MouseAcceleration 0",
        ])

    os.makedirs(CLIENT_DIR, exist_ok=True)
    with open(AUTOEXEC_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Ensure CustomMod_PTBR.Res00 is registered in Default.archcfg if present
    mod_mounted = False
    if os.path.exists(ARCHCFG_PATH):
        with open(ARCHCFG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            arch_lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        mod_entry = r"Game\CustomMod_PTBR.Res00"
        mod_full = os.path.join(CLIENT_DIR, mod_entry)
        if enable_ptbr_mod and os.path.exists(mod_full):
            if mod_entry not in arch_lines:
                arch_lines.append(mod_entry)
                with open(ARCHCFG_PATH, "w", encoding="utf-8") as f:
                    f.write("\r\n".join(arch_lines) + "\r\n")
            mod_mounted = True

    return {
        "resolution": f"{screen_w}x{screen_h}",
        "fov": fov,
        "raw_mouse": raw_mouse,
        "borderless": borderless,
        "max_fps": max_fps,
        "custom_mod_mounted": mod_mounted,
        "autoexec_path": AUTOEXEC_PATH,
    }


def enforce_borderless_window(window_titles=None, timeout_sec: float = 15.0) -> bool:
    """Polls for the LithTech D3D9 window and converts it into Borderless Fullscreen."""
    if os.name != "nt":
        return False
    if not window_titles:
        window_titles = [
            "District 187: Sin Streets (Ultra HD)",
            "District 187: Sin Streets",
            "S2",
            "TheRaw",
        ]

    user32 = ctypes.windll.user32
    screen_w, screen_h = get_primary_monitor_resolution()
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        for title in window_titles:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                new_style = style & ~(WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
                user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
                user32.SetWindowPos(
                    hwnd, 0, 0, 0, screen_w, screen_h,
                    SWP_FRAMECHANGED | SWP_SHOWWINDOW | SWP_NOZORDER
                )
                return True
        time.sleep(0.5)
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="District 187 Windows 11 QoL Optimizer")
    parser.add_argument("--fov", type=int, default=95)
    parser.add_argument("--borderless", action="store_true", default=True)
    parser.add_argument("--watch-window", action="store_true", help="Wait for TheRaw.exe window and make it borderless")
    args = parser.parse_args()

    res = apply_qol_profile(fov=args.fov, raw_mouse=True, borderless=args.borderless)
    print("[+] QoL Profile Applied:", json.dumps(res, indent=2))
    if args.watch_window:
        enforce_borderless_window(timeout_sec=12.0)
