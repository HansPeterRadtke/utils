#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI Interface Test Script (X11 / LXDE)

This script checks if required tools are installed (wmctrl, xdotool),
then fetches the top-level windows and prints them cleanly.
"""

import subprocess
import shutil
import sys


def check_dependencies():
    print("[DEBUG] Checking dependencies...")
    missing = []
    for tool in ["wmctrl", "xdotool"]:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        print(f"[ERROR] Missing tools: {', '.join(missing)}")
        sys.exit(1)
    print("[DEBUG] All dependencies found.")


def get_top_level_windows():
    print("[DEBUG] Fetching top-level windows via wmctrl...")
    try:
        output = subprocess.check_output(["wmctrl", "-l"], text=True)
    except Exception as e:
        print(f"[ERROR] Failed to run wmctrl: {e}")
        return []

    windows = []
    for line in output.strip().split("\n"):
        parts = line.split(None, 3)
        if len(parts) == 4:
            wid, desktop, pid, title = parts
            windows.append({
                "id": wid,
                "desktop": desktop,
                "title": title
            })
    return windows


def main():
    print("[DEBUG] Starting UIInterface test...")
    check_dependencies()
    windows = get_top_level_windows()

    if not windows:
        print("[INFO] No top-level windows found.")
    else:
        print("[INFO] Top-level windows:")
        for w in windows:
            print(f"- ID: {w['id']} | Desktop: {w['desktop']} | Title: {w['title']}")

    print("[DEBUG] UIInterface test finished.")


if __name__ == "__main__":
    main()