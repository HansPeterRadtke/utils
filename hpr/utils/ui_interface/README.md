# UI Interface

A **command-line interface for interacting with windows and applications** on X11 (LXDE on Raspberry Pi).  
Provides functions for listing, focusing, closing, launching applications, sending keystrokes, and interacting with window elements via accessibility (AT-SPI).

## Features
- List top-level windows
- Focus a window
- Send keystrokes to a window
- Close a window
- Launch applications (from command or from system menu)
- List available programs from the system start menu (`.desktop` files)
- List interactable elements (menus, buttons, text fields)
- Filter only **visible** interactable elements (clean output)
- Type directly into document fields
- Read contents of document fields
- Click menus and buttons
- Includes test scripts (automated and CLI)

## Installation
Requires external tools:
```
sudo apt install wmctrl xdotool python3-pyatspi
```

## Usage

### Python Module
Import functions from the module:

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

### CLI
Run directly as a module:
```
python3 -m hpr.utils.ui_interface
```
This will:
- List windows
- List available programs

### Tests
- `tests/full_test.py` → Integration test
  - Lists programs and windows
  - If gedit is open, writes a test string to the text buffer
  - Reads the buffer back
  - Verifies roundtrip success

## License
MIT