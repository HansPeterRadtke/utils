#!/usr/bin/env python3
"""Meaningful local integration checks; never sends email or deletes existing mail."""
import base64
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import make_msgid
import hashlib
import hmac
import imaplib
import json
import os
from pathlib import Path
import secrets
import smtplib
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path("/data/var/mail")
CFG = json.loads((ROOT / "config.json").read_text()) if (ROOT / "config.json").exists() else {}
ATTACHMENT = bytes(range(256)) * 257

def imap():
    client = imaplib.IMAP4("127.0.0.1", CFG["imap_port"], timeout=10)
    client.login(CFG["account"], (ROOT / "secrets/local-password").read_text().strip())
    return client

def test_cookie(role="admin", expired=False):
    state = json.loads(Path("/data/var/web_portal/session_state.json").read_text())
    data = {"host": "raspi", "role": role, "sid": "mail-test-" + secrets.token_hex(12),
            "csrf": secrets.token_hex(16), "rev": state["role_revisions"].get(role, 0),
            "exp": int(time.time()) + (-60 if expired else 120)}
    enc = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    key = Path(CFG["portal_secret"]).read_bytes().strip()
    sig = base64.urlsafe_b64encode(hmac.new(key, enc.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    return "infra_portal_session=" + enc + "." + sig

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fetch(path, cookie="", port=8080, data=None):
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
         headers={"Cookie": cookie, "Host": "raspi.jonnyontherun.org", "X-Forwarded-Proto": "https"})
    try:
        result = urllib.request.build_opener(NoRedirect).open(request, timeout=12)
    except urllib.error.HTTPError as error:
        result = error
    return result.status, result.headers, result.read()

@unittest.skipUnless(bool(CFG) and (__name__ == "__main__" or os.environ.get("MAIL_SERVICE_INTEGRATION_TESTS") == "1"), "Explicit opt-in and deployed Raspi mail services required")
class LocalMailTest(unittest.TestCase):
    def test_lmtp_imap_external_attachments(self):
        folder = "Mail-setup-tests"
        message = EmailMessage(policy=policy.SMTP)
        message["From"] = CFG["account"]
        message["To"] = CFG["account"]
        message["Subject"] = "Local mail setup verification"
        message["Message-ID"] = make_msgid(domain="raspi.local")
        message.set_content("Local integration test. No email was sent over the internet.")
        message.add_attachment(ATTACHMENT, maintype="application", subtype="octet-stream", filename="attachment-test.bin")
        with imap() as client:
            self.assertEqual(client.create(folder)[0], "OK")
            try:
                account, domain = CFG["account"].split("@")
                with smtplib.LMTP(str(ROOT / "run/lmtp"), timeout=10) as lmtp:
                    failures = lmtp.sendmail(CFG["account"], [f"{account}+{folder}@{domain}"], message.as_bytes())
                    self.assertEqual(failures, {})
                self.assertEqual(client.select(folder)[0], "OK")
                result, ids = client.uid("search", None, "ALL")
                self.assertEqual(result, "OK")
                self.assertEqual(len(ids[0].split()), 1)
                result, data = client.uid("fetch", ids[0], "(BODY.PEEK[])")
                restored = BytesParser(policy=policy.default).parsebytes(next(item[1] for item in data if isinstance(item, tuple)))
                self.assertEqual(restored["Message-ID"], message["Message-ID"])
                self.assertEqual(next(restored.iter_attachments()).get_payload(decode=True), ATTACHMENT)
                digest = hashlib.sha256(ATTACHMENT).hexdigest()
                matching = [p for p in (ROOT / "attachments").rglob("*") if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == digest]
                self.assertTrue(matching, "Dovecot must physically separate the decoded attachment")
            finally:
                client.close()
                client.delete(folder)

    def test_gateway_rejects_missing_guest_expired_and_tampered_sessions(self):
        for cookie in ["", test_cookie("public"), test_cookie(expired=True), test_cookie() + "tampered"]:
            self.assertEqual(fetch("/auth", cookie, CFG["gateway_port"])[0], 401)
            self.assertEqual(fetch("/mail/", cookie)[0], 303)
        self.assertEqual(fetch("/auth", test_cookie(), CFG["gateway_port"])[0], 200)

    def test_setup_requires_csrf_and_does_not_persist_bad_credentials(self):
        before = (ROOT / "secrets/gmail-app-password").exists()
        code, _, _ = fetch("/mail-setup/", test_cookie(), data=b"csrf=invalid&password=invalid")
        self.assertEqual(code, 403)
        self.assertEqual((ROOT / "secrets/gmail-app-password").exists(), before)
        code, _, body = fetch("/mail-setup/", test_cookie())
        self.assertEqual(code, 200)
        self.assertIn(b"Google app password", body)

    def test_roundcube_admin_sso(self):
        cookie = test_cookie()
        code, headers, body = fetch("/mail/", cookie)
        self.assertIn(code, (302, 303), body[:200])
        rc_cookies = {}
        for value in headers.get_all("Set-Cookie", []):
            key, value = value.split(";", 1)[0].split("=", 1)
            rc_cookies[key] = value
        self.assertIn("roundcube_sessid", rc_cookies)
        cookie += "; " + "; ".join(f"{k}={v}" for k, v in rc_cookies.items())
        code, _, body = fetch("/mail/?_task=mail", cookie)
        self.assertEqual(code, 200)
        self.assertIn(b'"task":"mail"', body)
        self.assertNotIn(b"Connection to storage server failed", body)
        self.assertIn(b"compose", body)


    def test_gmail_discovery_and_non_destructive_import_configuration(self):
        import configparser
        import tempfile
        import mail_service
        special = [b'(\\All) "/" "[Gmail]/All Mail"', b'(\\Sent) "/" "[Gmail]/Sent Mail"',
                   b'(\\Drafts) "/" "[Gmail]/Entw&APw-rfe"', b'(\\Junk) "/" "[Gmail]/Spam"',
                   b'(\\Trash) "/" "[Gmail]/Trash"']
        folders = mail_service.discover_folders(special)
        self.assertEqual(folders["\\drafts"], "[Gmail]/Entw\u00fcrfe")
        original = mail_service.ROOT
        try:
            with tempfile.TemporaryDirectory() as temporary:
                mail_service.ROOT = Path(temporary)
                (Path(temporary) / "config.json").write_text(json.dumps(CFG))
                mail_service.configure_getmail(folders)
                configs = list(Path(temporary).glob("getmail/*/getmailrc"))
                self.assertEqual(len(configs), 6)
                for path in configs:
                    config = configparser.ConfigParser()
                    config.read(path)
                    self.assertFalse(config.getboolean("options", "delete"))
                    self.assertEqual(config["retriever"]["ca_certs"], "/etc/ssl/certs/ca-certificates.crt")
                    self.assertEqual(config["destination"]["type"], "MDA_lmtp")
        finally:
            mail_service.ROOT = original

if __name__ == "__main__":
    unittest.main(verbosity=2)
