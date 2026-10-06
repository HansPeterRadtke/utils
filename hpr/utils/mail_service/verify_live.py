#!/usr/bin/env python3
"""Live self-addressed webmail test. Run once per explicitly requested verification."""
from email import policy
from email.parser import BytesParser
import fcntl
import hashlib
import json
from pathlib import Path
import re
import secrets
import time
import requests
from test_local import ATTACHMENT, CFG, ROOT, imap, test_cookie
from verify_webmail import Fields
from mail_service import atomic_write, receive, status_update

STATE = ROOT / "verification/live-test.json"

def save(state):
    STATE.parent.mkdir(mode=0o700, exist_ok=True)
    atomic_write(STATE, json.dumps(state, indent=2) + "\n")

def send():
    if STATE.exists():
        existing = json.loads(STATE.read_text())
        if existing.get("send_started"):
            print("A send was already attempted; verify receipt instead of sending twice.")
            return
    state = {"subject": "Multiverse mail setup test " + secrets.token_hex(8),
             "attachment_sha256": hashlib.sha256(ATTACHMENT).hexdigest(),
             "recipient": CFG["account"], "created_at": int(time.time())}
    save(state)
    base = "http://127.0.0.1:8080"
    client = requests.Session()
    client.headers.update({"Host": "raspi.jonnyontherun.org", "X-Forwarded-Proto": "https"})
    client.cookies.set("infra_portal_session", test_cookie().split("=", 1)[1])
    def get(path):
        for _ in range(6):
            response = client.get(base + path, allow_redirects=False, timeout=15)
            for cookie in client.cookies:
                cookie.secure = False
            if response.status_code not in (302, 303):
                response.raise_for_status()
                return response
            path = response.headers["Location"]
        raise RuntimeError("Redirect loop")
    get("/mail/")
    response = get("/mail/?_task=mail&_action=compose")
    env = json.loads(re.search(r'rcmail.set_env\((\{.*?\})\);', response.text)[1])
    fields = Fields(); fields.feed(response.text)
    upload = client.post(base + "/mail/", params={"_task":"mail","_action":"upload",
        "_id":env["compose_id"],"_remote":"1","_uploadid":"live-mail-test"},
        data={"_token":env["request_token"]},
        files={"_attachments[]":("verification.bin",ATTACHMENT,"application/octet-stream")}, timeout=15)
    upload.raise_for_status()
    match = re.search(r'add2attachment_list\("([^"]+)"', upload.json().get("exec",""))
    if not match:
        raise RuntimeError("Webmail attachment upload did not succeed")
    fields.values.update({"_task":"mail","_action":"send","_id":env["compose_id"],
        "_token":env["request_token"],"_draft":"0","_is_html":"0",
        "_to":CFG["account"],"_subject":state["subject"],
        "_message":"This self-addressed message tests Multiverse Mail on Raspi: sending, receiving, attachment integrity, and backup recovery. No action is needed.",
        "_attachments":match[1],"_store_target":"Sent","_framed":"1"})
    fields.values.pop("_attachments[]",None)
    state["send_started"] = int(time.time())
    save(state)
    result = client.post(base + "/mail/?_task=mail&_action=send", data=fields.values, timeout=60)
    result.raise_for_status()
    # SMTP can have accepted mail even if the HTTP request fails. Do not retry sends automatically.
    with imap() as local:
        local.select("Sent", readonly=True)
        _, ids = local.uid("search",None,"SUBJECT",'"'+state["subject"]+'"')
        if not ids[0]:
            atomic_write(ROOT / "verification/send-response.txt", result.text)
            raise RuntimeError("No Sent copy found; inspect the private response and Gmail before retrying")
        _, data = local.uid("fetch",ids[0].split()[0],"(BODY.PEEK[])")
        message = BytesParser(policy=policy.default).parsebytes(next(v[1] for v in data if isinstance(v,tuple)))
        if hashlib.sha256(next(message.iter_attachments()).get_payload(decode=True)).hexdigest() != state["attachment_sha256"]:
            raise RuntimeError("Sent attachment differs from the uploaded file")
        state.update(webmail_sent=True, sent_message_id=str(message["Message-ID"]), message_id=str(message["Message-ID"]))
        save(state)
        print("Webmail sent the self-addressed message and saved its attachment intact.")

def verify():
    state = json.loads(STATE.read_text())
    deadline = time.time() + 45
    uid = None
    raw = None
    while time.time() < deadline:
        receive()
        with imap() as local:
            local.select("INBOX", readonly=True)
            result, ids = local.uid("search", None, "SUBJECT", '"' + state["subject"] + '"')
            matches = ids[0].split() if result == "OK" else []
            if len(matches) > 1:
                raise RuntimeError("The unique live-test subject matched more than one local Inbox message")
            if len(matches) == 1:
                uid = matches[0]
                _, data = local.uid("fetch", uid, "(BODY.PEEK[])")
                raw = next(v[1] for v in data if isinstance(v, tuple))
                break
        time.sleep(2)
    if raw is None:
        raise RuntimeError("The test message has not been retrieved yet; retry verification, not sending")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if str(message["Subject"]) != state["subject"]:
        raise RuntimeError("Unexpected message content")
    attachment = next(message.iter_attachments()).get_payload(decode=True)
    if hashlib.sha256(attachment).hexdigest() != state["attachment_sha256"]:
        raise RuntimeError("Received attachment failed byte-for-byte verification")
    state.update(received=True, local_folder="INBOX", local_uid=uid.decode(),
                 incoming_message_id=str(message["Message-ID"]), attachment_verified=True,
                 verified_at=int(time.time()))
    save(state)
    status_update(live_delivery_tested_at=int(time.time()),
        account_message="OAuth webmail send, Gmail push, local retrieval, and attachment integrity passed. Remote deletion remains disabled.")
    print("Live Roundcube send, Gmail receipt, local retrieval and attachment integrity all passed.")

if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=["send","verify"])
    args=parser.parse_args()
    send() if args.action=="send" else verify()
