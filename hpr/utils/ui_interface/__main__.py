#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from . import list_windows, list_available_programs


def main():
    print("[DEBUG] Listing windows:")
    for w in list_windows():
        print(f"{w['id']} | {w['title']}")

    print("\n[DEBUG] Listing available programs:")
    for p in list_available_programs():
        print(f"{p['id']} | {p['name']} | {p['exec']}")


if __name__ == "__main__":
    main()