#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI Test for UI Interface

Usage:
  python3 cli_test.py list
  python3 cli_test.py focus <window_id>
  python3 cli_test.py close <window_id>
  python3 cli_test.py launch <command>
  python3 cli_test.py send <window_id> <text>
"""

import sys
import hpr.utils.ui_interface as ui


def main():
    if len(sys.argv) < 2:
        print("Usage: cli_test.py [list|focus|close|launch|send] ...")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        windows = ui.list_windows()
        for w in windows:
            print(f"- ID: {w['id']} | Desktop: {w['desktop']} | Title: {w['title']}")

    elif cmd == "focus" and len(sys.argv) == 3:
        ui.focus_window(sys.argv[2])

    elif cmd == "close" and len(sys.argv) == 3:
        ui.close_window(sys.argv[2])

    elif cmd == "launch" and len(sys.argv) >= 3:
        command = " ".join(sys.argv[2:])
        ui.launch_app(command)

    elif cmd == "send" and len(sys.argv) >= 4:
        win_id = sys.argv[2]
        text = " ".join(sys.argv[3:])
        ui.send_keys(win_id, text)

    else:
        print("Invalid usage. See source for commands.")


if __name__ == "__main__":
    main()