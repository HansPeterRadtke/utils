#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pyatspi
import subprocess

__all__ = [
  "list_windows",
  "focus_window",
  "send_keys",
  "launch_app",
  "close_window",
  "list_visible_elements",
  "type_into_document",
  "read_document_text",
  "click_element",
  "list_available_programs",
  "launch_program"
]


def list_windows():
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            windows = []
            for line in lines:
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    win_id, desktop, pid, title = parts
                    windows.append({"id": win_id, "desktop": desktop, "pid": pid, "title": title})
            return windows
        else:
            return []
    except Exception:
        return []


def focus_window(win_id):
    try:
        subprocess.run(["wmctrl", "-ia", win_id])
        return True
    except Exception:
        return False


def send_keys(win_id, text):
    try:
        subprocess.run(["xdotool", "type", "--window", win_id, text])
        return True
    except Exception:
        return False


def launch_app(command):
    try:
        os.system(f"{command} & disown")
        return True
    except Exception:
        return False


def close_window(win_id):
    try:
        subprocess.run(["wmctrl", "-ic", win_id])
        return True
    except Exception:
        return False


def list_visible_elements(app_name):
    apps = pyatspi.Registry.getDesktop(0)
    target = None
    for app in apps:
        if app_name.lower() in app.name.lower():
            target = app
            break
    if not target:
        return []

    elements = []

    def walk(node, depth=0):
        try:
            role = node.getRoleName()
            name = node.name or ""
            state_set = node.getState()
        except Exception:
            return

        if (role in ("menu", "menu item", "button", "text")) and (state_set.contains(pyatspi.STATE_SHOWING) or state_set.contains(pyatspi.STATE_VISIBLE)):
            elements.append({
                "id": str(hash(node)),  # use real unique identifier
                "role": role,
                "name": name,
                "node": node
            })

        if depth < 15:
            for child in node:
                walk(child, depth + 1)

    walk(target)
    return elements


def type_into_document(app_name, text):
    elems = list_visible_elements(app_name)
    for e in elems:
        if e['role'] == 'text':
            try:
                editable = e['node'].queryEditableText()
                editable.insertText(0, text, len(text))
                return True
            except Exception:
                continue
    try:
        subprocess.run(["xdotool", "search", "--onlyvisible", "--name", app_name, "windowactivate", "--sync", "type", text])
        return True
    except Exception:
        return False


def read_document_text(app_name):
    elems = list_visible_elements(app_name)
    for e in elems:
        if e['role'] == 'text':
            try:
                text_iface = e['node'].queryText()
                contents = text_iface.getText(0, -1)
                return contents
            except Exception:
                continue
    return None


def click_element(elements, element_id):
    for e in elements:
        if e["id"] == element_id and e["role"] in ("menu", "menu item", "button"):
            try:
                action = e["node"].queryAction()
                action.doAction(0)
                return True
            except Exception:
                return False
    return False


def list_available_programs():
    program_dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
    programs = []
    idx = 1

    for d in program_dirs:
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.endswith(".desktop"):
                continue
            fpath = os.path.join(d, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    name, exec_cmd, comment = None, None, None
                    for line in f:
                        if line.startswith("Name=") and not name:
                            name = line.strip().split("=", 1)[1]
                        elif line.startswith("Exec=") and not exec_cmd:
                            exec_cmd = line.strip().split("=", 1)[1]
                        elif line.startswith("Comment=") and not comment:
                            comment = line.strip().split("=", 1)[1]
                    if name and exec_cmd:
                        programs.append({
                            "id": f"P{idx}",
                            "name": name,
                            "exec": exec_cmd,
                            "comment": comment or ""
                        })
                        idx += 1
            except Exception:
                continue
    return programs


def launch_program(exec_cmd):
    try:
        os.system(f"{exec_cmd} & disown")
        return True
    except Exception:
        return False