#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os


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
            except Exception as ex:
                print(f"[WARN] Could not read {fpath}: {ex}")
    return programs


if __name__ == "__main__":
    print("[DEBUG] Listing available programs...")
    for p in list_available_programs():
        print(f"{p['id']} | {p['name']} | {p['exec']} | {p['comment']}")