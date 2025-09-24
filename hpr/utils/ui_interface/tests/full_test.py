#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from hpr.utils import ui_interface as ui

TEST_STRING = "[UI_INTERFACE_FULL_TEST] successful roundtrip"

print("[FULL TEST] Listing available programs:")
programs = ui.list_available_programs()
for p in programs[:10]:
    print(f"{p['id']} | {p['name']} | {p['exec']}")

print("\n[FULL TEST] Listing windows:")
windows = ui.list_windows()
for w in windows:
    print(f"{w['id']} | {w['title']}")

# Look for gedit
print("\n[FULL TEST] Checking for gedit window:")
gedit_windows = [w for w in windows if "gedit" in w['title'].lower()]
if not gedit_windows:
    print("[INFO] gedit is not open, skipping text roundtrip test.")
else:
    print("[INFO] gedit found, running text roundtrip test.")

    # Type the test string into gedit
    success = ui.type_into_document("gedit", TEST_STRING + "\n")
    if not success:
        print("[ERROR] Failed to type into gedit.")
    else:
        # Read the content back
        content = ui.read_document_text("gedit")
        if content and TEST_STRING in content:
            print("[SUCCESS] Roundtrip test passed: string found in gedit document.")
        else:
            print("[FAIL] Roundtrip test failed: string not found.")