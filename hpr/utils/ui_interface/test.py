#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI Interface Test Script

This script checks if required tools are installed, then tests both the
Python API and the CLI for listing top-level windows and available programs.
"""

import subprocess
import shutil
import sys

from hpr.utils import ui_interface as ui


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


def test_python_api():
    print("[DEBUG] Testing Python API: list_windows() and list_available_programs()")
    windows = ui.list_windows()
    programs = ui.list_available_programs()

    print(f"[INFO] Found {len(windows)} open windows via Python API.")
    for w in windows[:5]:
        print(f"- {w}")

    print(f"[INFO] Found {len(programs)} available programs via Python API.")
    for p in programs[:5]:
        print(f"- {p}")


def test_cli():
    print("[DEBUG] Testing CLI: list-windows and list-programs")
    try:
        win_output = subprocess.check_output(["python3", "-m", "hpr.utils.ui_interface", "list-windows"], text=True)
        print("[CLI list-windows output]:")
        print(win_output.strip())
    except Exception as e:
        print(f"[ERROR] CLI list-windows failed: {e}")

    try:
        prog_output = subprocess.check_output(["python3", "-m", "hpr.utils.ui_interface", "list-programs"], text=True)
        print("[CLI list-programs output]:")
        print(prog_output.strip())
    except Exception as e:
        print(f"[ERROR] CLI list-programs failed: {e}")


def main():
    print("[DEBUG] Starting UIInterface test...")
    check_dependencies()
    test_python_api()
    test_cli()
    print("[DEBUG] UIInterface test finished.")


if __name__ == "__main__":
    main()