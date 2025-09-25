# UI Interface Module

The **UI Interface** module provides functionality to inspect and interact with running applications on Wayland/X11 systems via AT-SPI and command line tools. It can be used both as a Python library and from the command line.

## Python Usage

```python
from hpr.utils import ui_interface as ui

# List open windows
windows = ui.list_windows()

# Focus a window
ui.focus_window(windows[0]['id'])

# Send keys to a window
ui.send_keys(windows[0]['id'], "Hello World")

# Launch an application
ui.launch_app("gedit")

# Close a window
ui.close_window(windows[0]['id'])

# List visible elements in an application
ui.list_visible_elements("gedit")

# List all elements (including invisible ones)
ui.get_all_elements("gedit")

# Find elements by role or name
ui.find_elements("gedit", role="menu", name="File")

# List editable elements
ui.get_all_editable("firefox", search_text="address")

# Type into a document or text field
ui.type_into_document("gedit", "Test output")

# Read document text
print(ui.read_document_text("gedit"))

# Click on a menu or button
ui.click_element(elements, element_id)

# List available programs from desktop entries
programs = ui.list_available_programs()

# Launch a program by exec command
ui.launch_program(programs[0]['exec'])
```

## CLI Usage

The module can also be used from the command line:

```bash
python3 -m hpr.utils.ui_interface <command> [arguments]
```

### Available Commands

- `list-windows` → List all open windows
- `list-programs` → List all available programs from desktop entries
- `focus-window <win_id>` → Focus a specific window by ID
- `send-keys <win_id> <text>` → Send keys to a specific window
- `launch-app <command>` → Launch an application by command
- `close-window <win_id>` → Close a specific window
- `list-visible <app_name>` → List all visible elements of an application
- `list-all <app_name>` → List all elements (visible and invisible)
- `find <app_name> [--role ROLE] [--name NAME]` → Find elements by role and/or name
- `list-editable <app_name> [--search TEXT]` → List all editable fields, optionally filtering by text
- `type <app_name> <text>` → Type text into the first available editable field in the application
- `read <app_name>` → Read text from the first visible text field in the application
```
