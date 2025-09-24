# UI Interface Module

Interact with windows and applications on X11 (LXDE on Raspberry Pi). Provides commands for listing, focusing, closing, launching applications, sending keystrokes, and interacting with window elements via accessibility (AT-SPI).

---

## Installation

This module is part of the `hpr-utils` package.

Install the full repo in editable mode (from repo root):

```
pip install -e .
```

Dependencies:
```
sudo apt install wmctrl xdotool python3-pyatspi
```

---

## Functionality

### Python Functions
- `list_windows()` → list top-level windows
- `focus_window(win_id)` → focus a window
- `send_keys(win_id, text)` → send keystrokes
- `launch_app(command)` → launch an application by command
- `close_window(win_id)` → close a window
- `list_visible_elements(app_name)` → list only visible menus, buttons, and text fields
- `type_into_document(app_name, text)` → type into the main text editor area
- `read_document_text(app_name)` → read document contents
- `click_element(elements, element_id)` → click a menu, menu item, or button
- `list_available_programs()` → list all available programs from system start menu entries
- `launch_program(exec_cmd)` → launch a program by its menu entry command

---

## CLI Usage

From the repo root, run:

```
python3 -m hpr.utils.ui_interface
```

This will:
- List open windows
- List available programs

---

## Files

- `__init__.py`: Core functionality
- `__main__.py`: CLI wrapper
- `tests/full_test.py`: Integration test

---

## Tests

Run the integration test from repo root:

```
python3 -m hpr.utils.ui_interface.tests.full_test
```

Covers:
- Listing programs
- Listing windows
- If gedit is open: writing, reading, and verifying text roundtrip

---

## Notes

- Only works on X11 with AT-SPI accessibility enabled.
- If gedit is not running, the text roundtrip test is skipped.