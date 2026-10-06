#!/usr/bin/env python3
"""Install/check the user-level schedules that keep Google push integrations healthy."""
import argparse
import subprocess

BASE = "/data/src/github/utils/hpr/utils/google_service"
PYTHON = "/usr/bin/python3"
RUNTIME = "/data/var/google-service"
MARKER = "# multiverse-google-"


def jobs():
    listener = f"/usr/bin/flock -n {RUNTIME}/pubsub-listen.lock {PYTHON} {BASE}/google_service.py pubsub-listen >>{RUNTIME}/pubsub-listen.log 2>&1"
    smtp = f"/usr/bin/flock -n {RUNTIME}/smtp-bridge.lock {PYTHON} {BASE}/gmail_smtp_bridge.py >>{RUNTIME}/smtp-bridge.log 2>&1"
    webhook = f"/usr/bin/flock -n {RUNTIME}/webhook-gateway.lock {PYTHON} {BASE}/webhook_gateway.py >>{RUNTIME}/webhook-gateway.log 2>&1"
    return [
        f"@reboot {listener} {MARKER}pubsub-start",
        f"* * * * * {listener} {MARKER}pubsub-supervisor",
        f"@reboot {smtp} {MARKER}smtp-start",
        f"* * * * * {smtp} {MARKER}smtp-supervisor",
        f"@reboot {webhook} {MARKER}webhook-start",
        f"* * * * * {webhook} {MARKER}webhook-supervisor",
        f"11 2 * * * /usr/bin/flock -n {RUNTIME}/calendar-watch.lock {PYTHON} {BASE}/google_service.py calendar-watch >/dev/null 2>&1 {MARKER}calendar-watch",
        f"21 2 * * * /usr/bin/flock -n {RUNTIME}/drive-watch.lock {PYTHON} {BASE}/google_service.py drive-watch >/dev/null 2>&1 {MARKER}drive-watch",
        f"13 3 * * * /usr/bin/flock -n {RUNTIME}/gmail-watch.lock {PYTHON} {BASE}/google_service.py gmail-watch >/dev/null 2>&1 {MARKER}gmail-watch",
        f"17 */6 * * * /usr/bin/flock -n {RUNTIME}/gmail-sync.lock {PYTHON} {BASE}/google_service.py gmail-sync >/dev/null 2>&1 {MARKER}gmail-sync",
        f"31 */6 * * * /usr/bin/flock -n {RUNTIME}/calendar-sync.lock {PYTHON} {BASE}/google_service.py calendar-sync >/dev/null 2>&1 {MARKER}calendar-sync",
        f"43 */6 * * * /usr/bin/flock -n {RUNTIME}/drive-sync.lock {PYTHON} {BASE}/google_service.py drive-sync >/dev/null 2>&1 {MARKER}drive-sync",
    ]


def current_lines():
    proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "Unable to read crontab")
    return proc.stdout.splitlines()


def install():
    keep = [line for line in current_lines() if MARKER not in line]
    desired = jobs()
    content = "\n".join(keep + desired) + "\n"
    proc = subprocess.run(["crontab", "-"], input=content, text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "Unable to install crontab")
    print(f"installed={len(desired)}")
    return 0


def check():
    current = set(current_lines())
    missing = [line for line in jobs() if line not in current]
    extra = [line for line in current if MARKER in line and line not in set(jobs())]
    print(f"managed={len(jobs())} missing={len(missing)} extra={len(extra)}")
    if missing:
        for line in missing:
            print("missing: " + line)
    if extra:
        for line in extra:
            print("extra: " + line)
    return 1 if missing or extra else 0


def show():
    for line in jobs():
        print(line)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Install/check Multiverse Google service cron jobs")
    parser.add_argument("action", choices=("install", "check", "show"), nargs="?", default="check")
    args = parser.parse_args()
    return {"install": install, "check": check, "show": show}[args.action]()


if __name__ == "__main__":
    raise SystemExit(main())
