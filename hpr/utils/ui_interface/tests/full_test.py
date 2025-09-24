#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hpr.utils import ui_interface as ui

print("[FULL TEST] Listing windows:")
for w in ui.list_windows():
    print(f"{w['id']} | {w['title']}")

print("\n[FULL TEST] Listing available programs:")
programs = ui.list_available_programs()
for p in programs[:10]:
    print(f"{p['id']} | {p['name']} | {p['exec']}")

print("\n[FULL TEST] Listing visible elements in gedit:")
elems = ui.list_visible_elements("gedit")
for e in elems:
    print(f"{e['id']} | {e['role']} | {e['name']}")

print("\n[FULL TEST] Typing into gedit:")
ui.type_into_document("gedit", "Hello from full module test!\n")

print("\n[FULL TEST] Reading from gedit:")
text = ui.read_document_text("gedit")
print(text)

print("\n[FULL TEST] Launching Firefox:")
firefox = [p for p in programs if "Firefox" in p['name']]
if firefox:
    ui.launch_program(firefox[0]['exec'])
    print("Launched Firefox")
else:
    print("Firefox not found in programs list")