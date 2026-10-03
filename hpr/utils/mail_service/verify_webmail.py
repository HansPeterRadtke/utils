#!/usr/bin/env python3
"""Exercise webmail compose, attachment upload, draft storage and reply without SMTP."""
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
import json
import re
import secrets
import requests
from test_local import ATTACHMENT, CFG, imap, test_cookie

class Fields(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "input" and a.get("name"):
            self.values[a["name"]] = a.get("value", "")

def main():
    base = "http://127.0.0.1:8080"
    client = requests.Session()
    client.headers.update({"Host": "raspi.jonnyontherun.org", "X-Forwarded-Proto": "https"})
    client.cookies.set("infra_portal_session", test_cookie().split("=", 1)[1])
    def get(path):
        for _ in range(6):
            response = client.get(base + path, allow_redirects=False, timeout=15)
            # The production cookies remain Secure. This client talks to the local HTTP bridge.
            for cookie in client.cookies:
                cookie.secure = False
            if response.status_code not in (302, 303):
                response.raise_for_status()
                return response
            path = response.headers["Location"]
        raise RuntimeError("Redirect loop")
    get("/mail/")
    compose = get("/mail/?_task=mail&_action=compose")
    env = json.loads(re.search(r'rcmail.set_env\((\{.*?\})\);', compose.text)[1])
    fields = Fields()
    fields.feed(compose.text)
    upload = client.post(base + "/mail/", params={"_task": "mail", "_action": "upload",
        "_id": env["compose_id"], "_remote": "1", "_uploadid": "mail-test"},
        data={"_token": env["request_token"]},
        files={"_attachments[]": ("webmail-test.bin", ATTACHMENT, "application/octet-stream")},
        timeout=15)
    assert upload.status_code == 200
    upload_code = upload.json().get("exec", "")
    match = re.search(r'add2attachment_list",\s*"([^"]+)"', upload_code)
    if not match:
        match = re.search(r'add2attachment_list\("([^"]+)"', upload_code)
    assert match, upload.text[:500]
    attachment_id = match[1]
    subject = "Webmail verification " + secrets.token_hex(8)
    fields.values.update({"_task": "mail", "_action": "send", "_id": env["compose_id"],
        "_token": env["request_token"], "_draft": "1", "_is_html": "0",
        "_to": CFG["account"], "_subject": subject, "_message": "Local webmail draft with attachment.",
        "_attachments": attachment_id, "_store_target": "Drafts", "_framed": "1"})
    fields.values.pop("_attachments[]", None)
    draft = client.post(base + "/mail/?_task=mail&_action=send",
                        data=fields.values, timeout=15)
    assert draft.status_code == 200
    with imap() as local:
        local.select("Drafts")
        _, ids = local.uid("search", None, "SUBJECT", '"' + subject + '"')
        assert len(ids[0].split()) == 1, draft.text[:500]
        uid = ids[0]
        try:
            _, raw = local.uid("fetch", uid, "(BODY.PEEK[])")
            saved = BytesParser(policy=policy.default).parsebytes(next(v[1] for v in raw if isinstance(v, tuple)))
            assert saved["Subject"] == subject
            assert next(saved.iter_attachments()).get_payload(decode=True) == ATTACHMENT
            reply = get("/mail/?_task=mail&_action=compose&_reply_uid=" + uid.decode() + "&_mbox=Drafts")
            assert "Re: " + subject in reply.text
            print(json.dumps({"compose": "ok", "attachment_upload": "ok", "draft_roundtrip": "ok",
                              "reply_composer": "ok", "external_email_sent": False}))
        finally:
            local.uid("store", uid, "+FLAGS.SILENT", "(\\Deleted)")
            assert local.uid("EXPUNGE", uid)[0] == "OK"

if __name__ == "__main__":
    main()
