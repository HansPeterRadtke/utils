#!/usr/bin/env python3
"""Restore the actual Gmail round-trip test from Nitro, then optionally delete only that test upstream."""
from email import policy
from email.parser import BytesParser
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
from mail_service import ROOT, settings, backup, status_update
from verify_live import STATE, save

def check_message(raw, state):
    message=BytesParser(policy=policy.default).parsebytes(raw)
    if str(message["Subject"]) != state["subject"]:
        raise RuntimeError("Message subject mismatch")
    attachment=next(message.iter_attachments()).get_payload(decode=True)
    if hashlib.sha256(attachment).hexdigest()!=state["attachment_sha256"]:
        raise RuntimeError("Attachment mismatch")
    return message

def restore():
    state=json.loads(STATE.read_text())
    if not state.get("received") or not state.get("attachment_verified"):
        raise RuntimeError("Live receipt and attachment verification are required first")
    cfg=settings()
    with (ROOT/"job.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        snapshot=backup()
        env=dict(os.environ, RESTIC_REPOSITORY=cfg["backup_repository"],
                 RESTIC_PASSWORD_FILE=str(ROOT/"secrets/backup-password"))
        target=Path(tempfile.mkdtemp(prefix="gmail-restore-",dir="/data/tmp"))
        try:
            subprocess.run(["restic","restore",snapshot,"--target",str(target)],env=env,check=True,
                stdout=subprocess.DEVNULL,timeout=300)
            root=target/"data/var/mail"
            raw=subprocess.run(["doveadm","-c","/etc/local-mail/dovecot.conf",
                "-o",f"mail_location=sdbox:{root}/mailbox",
                "-o",f"mail_attachment_dir={root}/attachments",
                "-o",f"mail_home={root}/home","fetch","-u",cfg["account"],"text",
                "mailbox",state["local_folder"],"uid",state["local_uid"]],
                check=True,capture_output=True).stdout
            if not raw.startswith(b"text:"):
                raise RuntimeError("The restored mailbox did not contain the test message")
            check_message(raw[len(b"text:"):].lstrip(b" \r\n"),state)
            google_root=target/"data/var/google-service"
            live_google=Path("/data/var/google-service")
            restored_token=json.loads((google_root/"oauth-token.json").read_text())
            live_token=json.loads((live_google/"oauth-token.json").read_text())
            if restored_token.get("refresh_token") != live_token.get("refresh_token"):
                raise RuntimeError("OAuth refresh-token recovery check failed")
            if "refresh_token_expires_in" in restored_token:
                raise RuntimeError("Restored OAuth token unexpectedly has a Testing-mode expiry")
            for name in ("gmail-sync.sqlite3","calendar.sqlite3","drive.sqlite3","events.sqlite3"):
                db=google_root/"backup-metadata"/name
                if db.exists():
                    with sqlite3.connect(db) as conn:
                        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise RuntimeError(name + " recovery integrity check failed")
            state.update(backup_restored=True,restored_snapshot=snapshot,restored_at=int(time.time()))
            save(state)
            status_update(live_restore_tested_at=int(time.time()))
            print("Actual Gmail test email, attachment, Production OAuth token, and Google runtime databases restored successfully from Nitro.")
        finally:
            shutil.rmtree(target)

if __name__=="__main__":
    restore()
