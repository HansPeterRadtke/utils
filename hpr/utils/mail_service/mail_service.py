#!/usr/bin/env python3
"""Private local mail archive. Gmail transport uses the local OAuth Google service."""
from __future__ import annotations
import argparse
import fcntl
import html
import hmac
import http.server
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import urllib.parse

ROOT = Path(os.environ.get("MAIL_SERVICE_ROOT", "/data/var/mail"))
SOURCE = Path(__file__).resolve().parent
GOOGLE_ROOT = Path("/data/var/google-service")

def settings():
    return json.loads((ROOT / "config.json").read_text())

def atomic_write(path, data, mode=0o600):
    path = Path(path)
    tmp = path.with_name(path.name + ".new")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

def status_update(**values):
    path = ROOT / "status.json"
    try:
        status = json.loads(path.read_text())
    except (OSError, ValueError):
        status = {}
    status.update(values)
    atomic_write(path, json.dumps(status, indent=2) + "\n")
    return status

def backup():
    cfg = settings()
    env = dict(os.environ, RESTIC_REPOSITORY=cfg["backup_repository"],
               RESTIC_PASSWORD_FILE=str(ROOT / "secrets/backup-password"))
    # SQLite's backup API gives consistent database copies while services stay live.
    live_db = ROOT / "roundcube/roundcube.db"
    (ROOT / "backup-metadata").mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(live_db) as source, sqlite3.connect(ROOT / "backup-metadata/roundcube.sqlite3") as target:
        source.backup(target)
    google_backup = GOOGLE_ROOT / "backup-metadata"
    google_backup.mkdir(parents=True, exist_ok=True)
    google_databases = ("gmail-sync.sqlite3", "calendar.sqlite3", "drive.sqlite3", "events.sqlite3")
    for name in google_databases:
        source_path = GOOGLE_ROOT / name
        target_path = google_backup / name
        if source_path.exists():
            with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
                source.backup(target)
            target_path.chmod(0o600)
        else:
            target_path.unlink(missing_ok=True)
    excludes = [
        str(ROOT / "run"), str(ROOT / "roundcube/temp"), str(ROOT / "roundcube/roundcube.db*"),
        str(ROOT / "roundcube/logs"), str(ROOT / "job.lock"),
        str(GOOGLE_ROOT / "*.lock"), str(GOOGLE_ROOT / "*.log"), str(GOOGLE_ROOT / "cloud-setup-wait.out"),
    ]
    for name in google_databases:
        excludes.extend((str(GOOGLE_ROOT / name), str(GOOGLE_ROOT / (name + "-wal")), str(GOOGLE_ROOT / (name + "-shm"))))
    command = ["restic", "backup", "--json", "--tag", "raspi-mail"]
    for value in excludes:
        command.extend(("--exclude", value))
    command.extend((str(ROOT), str(GOOGLE_ROOT)))
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=1800)
    if result.returncode:
        status_update(backup_error="Backup failed; inspect the private service logs.")
        raise RuntimeError("Encrypted backup failed")
    summaries = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    summary = next((item for item in summaries if item.get("message_type") == "summary"), None)
    if not summary or not summary.get("snapshot_id"):
        raise RuntimeError("Backup returned no snapshot identifier")
    status_update(backup_error=None, backup_at=int(time.time()), backup_snapshot=summary["snapshot_id"])
    return summary["snapshot_id"]

def receive():
    with (ROOT / "job.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        proc = subprocess.run(["/usr/bin/python3", "/data/src/github/utils/hpr/utils/google_service/google_service.py", "gmail-sync"], capture_output=True, text=True, timeout=900)
        if proc.returncode:
            status_update(connected=False, receive_error="OAuth Gmail API synchronization failed.")
            raise RuntimeError("OAuth Gmail synchronization failed")
        status_update(receive_error=None, received_at=int(time.time()), connected=True, account_message="Google OAuth connected; Gmail API synchronization active.")


def portal_session(cookie):
    cfg = settings()
    sys.path.insert(0, cfg["portal_helper"])
    from portal_session import verify_session_cookie
    return verify_session_cookie(cookie, cfg["portal_secret"], cfg["portal_host"], required_role="admin")

class Gateway(http.server.BaseHTTPRequestHandler):
    server_version = "Mail"
    sys_version = ""
    def log_message(self, *args):
        pass  # Never record cookies, credentials, or POST bodies.

    def respond(self, code, body="", content_type="text/html; charset=utf-8", location=None):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        if location:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(data)

    def page(self, session, message=""):
        cfg = settings()
        try:
            state = json.loads((ROOT / "status.json").read_text())
        except (OSError, ValueError):
            state = {}
        connected = bool(state.get("connected"))
        connection = "Gmail connected" if connected else "Connect Gmail"
        notice = message or state.get("account_message") or "Google OAuth is managed by the local Google service."
        body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Multiverse Mail</title>
<style>body{{font:18px system-ui;background:#101723;color:#eef2f6;max-width:42rem;margin:6vh auto;padding:1.5rem}}a{{color:#8fd4ff}}input,button{{font:inherit;padding:.7rem;border-radius:.4rem}}input{{width:90%;margin:.5rem 0 1rem}}button{{background:#a3dfb8;border:0;cursor:pointer}}.note{{padding:1rem;background:#203047;border-radius:.5rem}}small{{color:#b8c3d2}}</style>
<a href="/">Raspi</a><h1>Multiverse Mail</h1><p>{html.escape(cfg['account'])}</p>
<p><a href="/mail/">Open mailbox</a></p><h2>{connection}</h2><p class="note">{html.escape(notice)}</p>
<p>Google access is authenticated through OAuth by the local Google service. No Google password or app password is required here.</p>
<p><small>Mail is stored on Raspi, with encrypted backups on Nitro. Gmail server deletion remains off until the live download, backup, restore, and deletion tests pass.</small></p></html>"""
        self.respond(200, body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/health":
            cfg = settings()
            try:
                state = json.loads((ROOT / "status.json").read_text())
            except (OSError, ValueError):
                state = {}
            detail = state.get("receive_error") or ("Google OAuth connected" if Path("/data/var/google-service/oauth-token.json").exists() else "Google OAuth not connected")
            self.respond(200, json.dumps({"ok": True, "state": detail, "remote_deletion": False}), "application/json")
            return
        session = portal_session(self.headers.get("Cookie", ""))
        if not session:
            self.respond(401 if path == "/auth" else 303, location=None if path == "/auth" else "/")
            return
        if path == "/auth":
            self.respond(200, json.dumps({"ok": True, "sid": session["sid"]}), "application/json")
        elif path.rstrip("/") == "/mail-setup":
            self.page(session)
        else:
            self.respond(404, "Not found")

    def do_POST(self):
        if urllib.parse.urlsplit(self.path).path != "/mail-setup/":
            self.respond(404)
            return
        self.respond(410, "Google OAuth is managed by the local Google service. No app password setup is available.", "text/plain; charset=utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["serve", "receive", "backup"])
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == "serve":
        http.server.ThreadingHTTPServer(("127.0.0.1", settings()["gateway_port"]), Gateway).serve_forever()
    elif args.action == "receive":
        receive()
    elif args.action == "backup":
        with (ROOT / "job.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            print("Snapshot:", backup())

if __name__ == "__main__":
    main()
