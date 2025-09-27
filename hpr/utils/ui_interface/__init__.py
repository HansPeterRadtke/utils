#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pyatspi
import subprocess
import argparse

__all__ = [
  "list_windows",
  "focus_window",
  "send_keys",
  "launch_app",
  "close_window",
  "list_visible_elements",
  "get_all_elements",
  "find_elements",
  "get_all_editable",
  "type_into_document",
  "read_document_text",
  "click_element",
  "list_available_programs",
  "launch_program",
  "get_possible_actions",
  "perform_action",
  "type_into_element",
  "read_element_text",
  "main"
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


def _walk_elements(node, elements, depth=0, include_invisible=True):
    try:
        role = node.getRoleName()
        name = node.name or ""
        state_set = node.getState()
    except Exception:
        return

    if include_invisible or state_set.contains(pyatspi.STATE_SHOWING) or state_set.contains(pyatspi.STATE_VISIBLE):
        elements.append({
            "id": str(hash(node)),
            "role": role,
            "name": name,
            "node": node,
            "depth": depth
        })

    if depth < 30:
        for child in node:
            _walk_elements(child, elements, depth + 1, include_invisible)


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
    _walk_elements(target, elements, include_invisible=False)
    return elements


def get_all_elements(app_name):
    apps = pyatspi.Registry.getDesktop(0)
    target = None
    for app in apps:
        if app_name.lower() in app.name.lower():
            target = app
            break
    if not target:
        return []

    elements = []
    _walk_elements(target, elements, include_invisible=True)
    return elements


def find_elements(app_name, role=None, name=None):
    elems = get_all_elements(app_name)
    results = []
    for e in elems:
        if role and e['role'] != role:
            continue
        if name and name.lower() not in e['name'].lower():
            continue
        results.append(e)
    return results


def get_all_editable(app_name, search_text=None):
    elems = get_all_elements(app_name)
    results = []
    for e in elems:
        try:
            node = e['node']
            node.queryEditableText()
            if search_text:
                if search_text.lower() not in (e['name'] or '').lower():
                    continue
            results.append(e)
        except Exception:
            continue
    return results


def type_into_document(app_name, text):
    elems = list_visible_elements(app_name)
    for e in elems:
        if e['role'] in ('text', 'entry'):
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
        if e['role'] in ('text', 'entry'):
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


def get_element(app_name, element_id):
    elems = get_all_elements(app_name)
    for e in elems:
        if e['id'] == element_id:
            return e
    return None


def get_possible_actions(app_name, element_id):
    elem = get_element(app_name, element_id)
    if not elem:
        return []
    node = elem['node']
    try:
        action_iface = node.queryAction()
        num_actions = action_iface.nActions
        actions = [action_iface.getActionDescription(i) for i in range(num_actions)]
        return actions
    except Exception:
        return []


def perform_action(app_name, element_id, action_index=0):
    elem = get_element(app_name, element_id)
    if not elem:
        return False
    node = elem['node']
    try:
        action_iface = node.queryAction()
        if 0 <= action_index < action_iface.nActions:
            action_iface.doAction(action_index)
            return True
        return False
    except Exception:
        return False


def type_into_element(app_name, element_id, text, position=0):
    elem = get_element(app_name, element_id)
    if not elem:
        return False
    node = elem['node']
    try:
        editable = node.queryEditableText()
        editable.insertText(position, text, len(text))
        return True
    except Exception:
        return False


def read_element_text(app_name, element_id):
    elem = get_element(app_name, element_id)
    if not elem:
        return None
    node = elem['node']
    try:
        text_iface = node.queryText()
        return text_iface.getText(0, -1)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="UI Interface CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-windows")
    subparsers.add_parser("list-programs")

    parser_focus = subparsers.add_parser("focus-window")
    parser_focus.add_argument("win_id")

    parser_keys = subparsers.add_parser("send-keys")
    parser_keys.add_argument("win_id")
    parser_keys.add_argument("text")

    parser_launch = subparsers.add_parser("launch-app")
    parser_launch.add_argument("command")

    parser_close = subparsers.add_parser("close-window")
    parser_close.add_argument("win_id")

    parser_visible = subparsers.add_parser("list-visible")
    parser_visible.add_argument("app_name")

    parser_all = subparsers.add_parser("list-all")
    parser_all.add_argument("app_name")

    parser_find = subparsers.add_parser("find")
    parser_find.add_argument("app_name")
    parser_find.add_argument("--role", default=None)
    parser_find.add_argument("--name", default=None)

    parser_editable = subparsers.add_parser("list-editable")
    parser_editable.add_argument("app_name")
    parser_editable.add_argument("--search", default=None)

    parser_type = subparsers.add_parser("type")
    parser_type.add_argument("app_name")
    parser_type.add_argument("text")

    parser_read = subparsers.add_parser("read")
    parser_read.add_argument("app_name")

    parser_actions_list = subparsers.add_parser("list-actions")
    parser_actions_list.add_argument("app_name")
    parser_actions_list.add_argument("element_id")

    parser_perform = subparsers.add_parser("perform-action")
    parser_perform.add_argument("app_name")
    parser_perform.add_argument("element_id")
    parser_perform.add_argument("--index", type=int, default=0)

    parser_type_elem = subparsers.add_parser("type-element")
    parser_type_elem.add_argument("app_name")
    parser_type_elem.add_argument("element_id")
    parser_type_elem.add_argument("text")
    parser_type_elem.add_argument("--position", type=int, default=0)

    parser_read_elem = subparsers.add_parser("read-element")
    parser_read_elem.add_argument("app_name")
    parser_read_elem.add_argument("element_id")

    args = parser.parse_args()

    if args.command == "list-windows":
        print(list_windows())
    elif args.command == "list-programs":
        print(list_available_programs())
    elif args.command == "focus-window":
        print(focus_window(args.win_id))
    elif args.command == "send-keys":
        print(send_keys(args.win_id, args.text))
    elif args.command == "launch-app":
        print(launch_app(args.command))
    elif args.command == "close-window":
        print(close_window(args.win_id))
    elif args.command == "list-visible":
        print(list_visible_elements(args.app_name))
    elif args.command == "list-all":
        print(get_all_elements(args.app_name))
    elif args.command == "find":
        print(find_elements(args.app_name, role=args.role, name=args.name))
    elif args.command == "list-editable":
        print(get_all_editable(args.app_name, args.search))
    elif args.command == "type":
        print(type_into_document(args.app_name, args.text))
    elif args.command == "read":
        print(read_document_text(args.app_name))
    elif args.command == "list-actions":
        print(get_possible_actions(args.app_name, args.element_id))
    elif args.command == "perform-action":
        print(perform_action(args.app_name, args.element_id, args.index))
    elif args.command == "type-element":
        print(type_into_element(args.app_name, args.element_id, args.text, args.position))
    elif args.command == "read-element":
        print(read_element_text(args.app_name, args.element_id))

