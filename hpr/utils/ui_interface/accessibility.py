#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Accessibility functions for UI Interface

Uses pyatspi (AT-SPI) to introspect applications and list interactable elements,
and interact with them (click, type, read).
"""

import pyatspi
import subprocess


def list_interactable_elements(app_name):
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
        except Exception:
            return
        if role == "text":
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
    elems = list_interactable_elements(app_name)
    for e in elems:
        if e['role'] == 'text' and 'search' not in (e['name'] or '').lower():
            try:
                editable = e['node'].queryEditableText()
                editable.insertText(0, text, len(text))
                print(f"[INFO] Typed into document element {e['id']} via AT-SPI: {text}")
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
    elems = list_interactable_elements(app_name)
    found = False
    for e in elems:
        if e['role'] == 'text':
            try:
                text_iface = e['node'].queryText()
                contents = text_iface.getText(0, -1)
                print(f"[INFO] Element {e['id']} | name='{e['name']}' | text: {contents}")
                found = True
            except Exception as ex:
                print(f"[WARN] Could not read text from element {e['id']}: {ex}")
    if not found:
        print("[WARN] No text fields found at all.")
    return None


def click_element(elements, element_id):
    for e in elements:
        if e["id"] == element_id and e["role"] in ("menu", "menu item", "button"):
            try:
                action = e["node"].queryAction()
                action.doAction(0)
                print(f"[INFO] Clicked element {element_id} ({e['role']} - {e['name']})")
                return True
            except Exception as ex:
                print(f"[ERROR] Could not click element {element_id}: {ex}")
                return False
    print(f"[WARN] Element {element_id} not found or not clickable.")
    return False


if __name__ == "__main__":
    print("[DEBUG] Typing into gedit document...")
    type_into_document("gedit", "Yet another line via AT-SPI or fallback.\n")
    print("[DEBUG] Reading all text fields...")
    read_document_text("gedit")