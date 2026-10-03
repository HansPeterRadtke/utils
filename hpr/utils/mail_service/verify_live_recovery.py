#!/usr/bin/env python3
"""Restore the actual Gmail round-trip test from Nitro, then optionally delete only that test upstream."""
from email import policy
from email.parser import BytesParser
import fcntl
import hashlib
import imaplib
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import tempfile
import time
from mail_service import ROOT, settings, backup, atomic_write, status_update, discover_folders
from verify_live import STATE, save

def check_message(raw, state):
    message=BytesParser(policy=policy.default).parsebytes(raw)
    if str(message["Message-ID"]) != state["message_id"] or str(message["Subject"]) != state["subject"]:
        raise RuntimeError("Message identity mismatch")
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
            if (root/"secrets/gmail-app-password").read_bytes() != (ROOT/"secrets/gmail-app-password").read_bytes():
                raise RuntimeError("Credential recovery check failed")
            state.update(backup_restored=True,restored_snapshot=snapshot,restored_at=int(time.time()))
            save(state)
            status_update(live_restore_tested_at=int(time.time()))
            print("Actual Gmail test email, attachment and account credential restored successfully from Nitro.")
        finally:
            shutil.rmtree(target)

def quote(value):
    return '"' + value.replace("\\","\\\\").replace('"','\\"') + '"'

def delete_test():
    state=json.loads(STATE.read_text())
    if not all(state.get(k) for k in ("webmail_sent","received","attachment_verified","backup_restored")):
        raise RuntimeError("All live recovery gates must pass first")
    cfg=settings()
    if state["recipient"] != cfg["account"] or not state["subject"].startswith("Multiverse mail setup test "):
        raise RuntimeError("Only this run's self-addressed test message may be deleted")
    with imaplib.IMAP4_SSL("imap.gmail.com",ssl_context=ssl.create_default_context(),timeout=30) as c:
        c.login(cfg["account"],(ROOT/"secrets/gmail-app-password").read_text().strip())
        code, advertised = c.capability()
        capabilities = set(b" ".join(advertised).upper().split()) if code == "OK" else set()
        if b"MOVE" not in capabilities or b"UIDPLUS" not in capabilities:
            raise RuntimeError("Gmail must advertise targeted MOVE and UID EXPUNGE support")
        _,listing=c.list();folders=discover_folders(listing)
        # Folder names used here are ASCII on this account. Refuse unsupported encoding rather than guess.
        for value in (folders["\\all"],folders["\\trash"],folders["\\junk"]):
            value.encode("ascii")
        trash=quote(folders["\\trash"])
        if state.get("gmail_message_id"):
            gm_id=state["gmail_message_id"]
        else:
            c.select(quote(folders["\\all"]))
            code,ids=c.uid("search",None,"HEADER","Message-ID",quote(state["message_id"]))
            if code!="OK" or len(ids[0].split())!=1:
                raise RuntimeError("Expected exactly one matching Gmail test message")
            uid=ids[0]
            code,data=c.uid("fetch",uid,"(X-GM-MSGID BODY.PEEK[])")
            part=next(v for v in data if isinstance(v,tuple))
            check_message(part[1],state)
            match=re.search(rb"X-GM-MSGID (\d+)",part[0])
            if not match: raise RuntimeError("Gmail unique message identifier unavailable")
            gm_id=match[1].decode()
            state["gmail_message_id"]=gm_id;save(state)
            code,_=c.uid("MOVE",uid,trash)
            if code!="OK": raise RuntimeError("Moving test message to Gmail Trash failed")
        c.select(trash)
        code,ids=c.uid("search",None,"X-GM-MSGID",gm_id)
        if code!="OK": raise RuntimeError("Gmail Trash search failed")
        if ids[0]:
            if len(ids[0].split())!=1: raise RuntimeError("Unexpected duplicate Gmail identity")
            uid=ids[0]
            _,data=c.uid("fetch",uid,"(BODY.PEEK[])")
            check_message(next(v[1] for v in data if isinstance(v,tuple)),state)
            if c.uid("store",uid,"+FLAGS.SILENT","(\\Deleted)")[0]!="OK":
                raise RuntimeError("Marking test mail deleted failed")
            if c.uid("EXPUNGE",uid)[0]!="OK":
                raise RuntimeError("Targeted permanent deletion failed")
        # Never use broad EXPUNGE: it could remove unrelated messages marked deleted by another client.
        for folder in (folders["\\all"],folders["\\trash"],folders["\\junk"],"INBOX",folders["\\sent"]):
            c.select(quote(folder),readonly=True)
            code,ids=c.uid("search",None,"X-GM-MSGID",gm_id)
            if code!="OK" or ids[0]:
                raise RuntimeError("Test message is still present on Gmail")
    state.update(gmail_test_deleted=True,deleted_at=int(time.time()))
    save(state)
    status_update(gmail_test_deletion_tested_at=int(time.time()))
    print("Only the backed-up test message was permanently removed from Gmail; local copies remain.")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("action",choices=["restore","delete-test"])
    args=p.parse_args()
    restore() if args.action=="restore" else delete_test()
