"""
UI Interface Module for X11 (LXDE)

Provides functions to interact with top-level windows:
- List windows
- Focus a window
- Close a window
- Launch applications
- Send keystrokes/mouse events

Depends on: wmctrl, xdotool
"""

from .main import list_windows, focus_window, close_window, launch_app, send_keys