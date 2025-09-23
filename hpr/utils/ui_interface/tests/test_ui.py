#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test UI Interface Module

This script imports the ui_interface module and exercises its functions:
- List open windows
- Focus a window
- Send keys to a window
- Perform a simple system call (instead of launching a new terminal)
- Close a window (if needed)
"""

import time
import os
import hpr.utils.ui_interface as ui


def main():
    print("[DEBUG] Starting UIInterface test script...")

    # List windows
    windows = ui.list_windows()
    print("[INFO] Windows detected:")
    for w in windows:
        print(f"- ID: {w['id']} | Desktop: {w['desktop']} | Title: {w['title']}")

    if not windows:
        print("[WARN] No windows to test on.")
        return

    # Pick the first window for testing
    test_win = windows[0]['id']
    print(f"[DEBUG] Using window {test_win} for tests.")

    # Focus the window
    print("[TEST] Focusing the window...")
    ui.focus_window(test_win)
    time.sleep(1)

    # Send keys
    print("[TEST] Sending keys 'Hello from UIInterface!'...")
    ui.send_keys(test_win, "Hello from UIInterface!")
    time.sleep(1)

    # Simple system call instead of launching xterm
    print("[TEST] Performing a system call: 'echo TEST'...")
    os.system("echo TEST")

    print("[DEBUG] Test script finished.")


if __name__ == "__main__":
    main()