#!/usr/bin/env python3
"""Verify a Nitro snapshot can reconstruct a complete email and binary attachment."""
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import make_msgid
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
from test_local import imap, ROOT, CFG, ATTACHMENT
from mail_service import backup

def main():
    folder = "Restore-test-" + secrets.token_hex(6)
    target = Path(tempfile.mkdtemp(prefix="mail-restore-", dir="/data/tmp"))
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = message["To"] = CFG["account"]
    message["Subject"] = "Backup recovery verification"
    message["Message-ID"] = make_msgid(domain="raspi.local")
    message.set_content("Disposable local restore verification.")
    message.add_attachment(ATTACHMENT, maintype="application", subtype="octet-stream", filename="recovery-test.bin")
    env = dict(os.environ, RESTIC_REPOSITORY=CFG["backup_repository"],
               RESTIC_PASSWORD_FILE=str(ROOT / "secrets/backup-password"))
    try:
        with imap() as client:
            assert client.create(folder)[0] == "OK"
            assert client.append(folder, None, None, message.as_bytes())[0] == "OK"
        snapshot = backup()
        subprocess.run(["restic", "restore", snapshot, "--target", str(target)], env=env, check=True,
                       stdout=subprocess.DEVNULL, timeout=300)
        restored = target / "data/var/mail"
        command = ["doveadm", "-c", "/etc/local-mail/dovecot.conf",
                   "-o", f"mail_location=sdbox:{restored}/mailbox",
                   "-o", f"mail_attachment_dir={restored}/attachments",
                   "-o", f"mail_home={restored}/home",
                   "fetch", "-u", CFG["account"], "text", "mailbox", folder]
        raw = subprocess.run(command, check=True, capture_output=True).stdout
        assert raw.startswith(b"text:"), raw[:80]
        restored_message = BytesParser(policy=policy.default).parsebytes(raw[len(b"text:"):].lstrip(b" \r\n"))
        assert restored_message["Message-ID"] == message["Message-ID"]
        assert next(restored_message.iter_attachments()).get_payload(decode=True) == ATTACHMENT
        with sqlite3.connect(restored / "backup-metadata/roundcube.sqlite3") as database:
            assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # Verify every restored immutable secret byte and the Production OAuth credential.
        for secret in ("local-password", "roundcube-key", "backup-password"):
            assert (ROOT / "secrets" / secret).read_bytes() == (restored / "secrets" / secret).read_bytes()
        google_live = Path("/data/var/google-service")
        google_restored = target / "data/var/google-service"
        live_token = json.loads((google_live / "oauth-token.json").read_text())
        restored_token = json.loads((google_restored / "oauth-token.json").read_text())
        assert restored_token.get("refresh_token") == live_token.get("refresh_token")
        assert "refresh_token_expires_in" not in restored_token
        restored_google_dbs = []
        for name in ("gmail-sync.sqlite3", "calendar.sqlite3", "drive.sqlite3", "events.sqlite3"):
            db = google_restored / "backup-metadata" / name
            if db.exists():
                with sqlite3.connect(db) as database:
                    assert database.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                restored_google_dbs.append(name)
        print(json.dumps({"snapshot": snapshot, "message_restored": True, "attachment_bytes": len(ATTACHMENT),
                          "attachment_sha256": hashlib.sha256(ATTACHMENT).hexdigest(),
                          "webmail_database_integrity": "ok", "secret_files_restored": True,
                          "production_oauth_restored": True, "google_databases_restored": restored_google_dbs}))
    finally:
        with imap() as client:
            client.delete(folder)
        shutil.rmtree(target)

if __name__ == "__main__":
    main()
