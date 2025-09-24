#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyatspi
import subprocess


def list_visible_elements(app_name):
    apps = pyatspi.Registry.getDesktop(0)
    target = None
    for app in apps:
        if app_name.lower() in app.name.lower():
            target = app
            break
    if not target:
        print("[ERROR] Application not found.")
        return []

    elements = []
    idx = 1

    def walk(node, depth=0):
        nonlocal idx
        try:
            role = node.getRoleName()
            name = node.name or ""
            state_set = node.getState()
        except Exception:
            return

        if (role in ("menu", "menu item", "button", "text")) and (state_set.contains(pyatspi.STATE_SHOWING) or state_set.contains(pyatspi.STATE_VISIBLE)):
            elements.append({
                "id": f"E{idx}",
                "role": role,
                "name": name,
                "node": node
            })
            idx += 1

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
                print(f"[INFO] Typed into visible text element {e['id']}: {text}")
                return True
            except Exception as ex:
                print(f"[WARN] AT-SPI typing failed for element {e['id']}: {ex}")
    try:
        subprocess.run(["xdotool", "search", "--onlyvisible", "--name", app_name, "windowactivate", "--sync", "type", text])
        print(f"[INFO] Typed into {app_name} window via xdotool: {text}")
        return True
    except Exception as ex2:
        print(f"[ERROR] Fallback xdotool typing failed: {ex2}")
        return False


def read_document_text(app_name):
    elems = list_visible_elements(app_name)
    for e in elems:
        if e['role'] == 'text':
            try:
                text_iface = e['node'].queryText()
                contents = text_iface.getText(0, -1)
                print(f"[INFO] Read from visible text element {e['id']}: {contents}")
                return contents
            except Exception as ex:
                print(f"[WARN] Could not read from element {e['id']}: {ex}")
    print("[WARN] No visible document text field found.")
    return None


def click_element(elements, element_id):
    for e in elements:
        if e["id"] == element_id and e["role"] in ("menu", "menu item", "button"):
            try:
                action = e["node"].queryAction()
                action.doAction(0)
                print(f"[INFO] Clicked visible element {element_id} ({e['role']} - {e['name']})")
                return True
            except Exception as ex:
                print(f"[ERROR] Could not click element {element_id}: {ex}")
                return False
    print(f"[WARN] Element {element_id} not found or not clickable.")
    return False


if __name__ == "__main__":
    print("[DEBUG] Listing visible elements in gedit (correct state checks)...")
    elems = list_visible_elements("gedit")
    for e in elems:
        print(f"{e['id']} | role={e['role']} | name={e['name']}")
    print("[DEBUG] Typing and reading from document...")
    type_into_document("gedit", "Visible text test with proper state.\n")
    read_document_text("gedit")