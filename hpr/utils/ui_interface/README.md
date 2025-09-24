# UI Interface

A **command-line interface for interacting with windows** on X11 (LXDE on Raspberry Pi).  
Provides functions for listing, focusing, closing, launching applications, sending keystrokes, and interacting with window elements via accessibility (AT-SPI).

## Features
- List top-level windows
- Focus a window
- Send keystrokes to a window
- Close a window
- Launch applications
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
- `launch_app(command)` → launch applications
- `close_window(win_id)` → close a window
- `list_visible_elements(app_name)` → list only visible menus, buttons, and text fields
- `type_into_document(app_name, text)` → type into the main text editor area
- `read_document_text(app_name)` → read document contents
- `click_element(elements, element_id)` → click a menu, menu item, or button

### CLI Test
Run from the module test folder:
```
python3 cli_test.py list
python3 cli_test.py focus <window_id>
python3 cli_test.py close <window_id>
python3 cli_test.py launch <command>
python3 cli_test.py send <window_id> <text>
```

### Automated Test
```
python3 test_ui.py
```
This will:
- List windows
- Focus the first window
- Send keystrokes
- Perform a simple system call
- List visible interactable elements of gedit
- Write and read text from the document field

## License
MIT