# UI Interface

A **command-line interface for interacting with windows** on X11 (LXDE on Raspberry Pi).  
Provides functions for listing, focusing, closing, launching applications, and sending keystrokes to windows.

## Features
- List top-level windows
- Focus a window
- Send keystrokes to a window
- Close a window
- Launch applications
- Includes test scripts (automated and CLI)

## Installation
Requires external tools:
```
sudo apt install wmctrl xdotool
```

## Usage

### Python Module
```
from hpr.utils import ui_interface as ui

# List windows
windows = ui.list_windows()
for w in windows:
    print(w)

# Focus a window
ui.focus_window(windows[0]['id'])

# Send keystrokes
ui.send_keys(windows[0]['id'], "Hello!")

# Launch an application
ui.launch_app("lxterminal")

# Close a window
ui.close_window(windows[0]['id'])
```

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

## License
MIT