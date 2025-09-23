#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI Interface Main Module

Provides core functions for interacting with windows on X11 (LXDE) using wmctrl and xdotool.
"""

import subprocess
import shutil


def _check_tool(tool):
    if shutil.which(tool) is None:
        raise RuntimeError(f"Required tool '{tool}' not found in PATH.")


def list_windows():
    """Return a list of top-level windows."""
    _check_tool("wmctrl")
    result = subprocess.check_output(["wmctrl", "-l"], text=True)
    windows = []
    for line in result.strip().split("\n"):
        parts = line.split(None, 3)
        if len(parts) == 4:
            wid, desktop, pid, title = parts
            windows.append({
                "id": wid,
                "desktop": desktop,
                "title": title
            })
    return windows


def focus_window(win_id):
    """Focus a window by ID."""
    _check_tool("wmctrl")
    subprocess.run(["wmctrl", "-ia", win_id])


def close_window(win_id):
    """Close a window by ID."""
    _check_tool("wmctrl")
    subprocess.run(["wmctrl", "-ic", win_id])


def launch_app(command):
    """Launch a new application."""
    subprocess.Popen(command, shell=True)


def send_keys(win_id, keys):
    """Send keystrokes to a window by ID."""
    _check_tool("xdotool")
    subprocess.run(["xdotool", "type", "--window", win_id, keys])