#!/usr/bin/env python3
"""Health and integration tests for the Multiverse Google service."""
import argparse
import imaplib
import json
from pathlib import Path
import socket
import stat
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
RUNTIME = Path('/data/var/google-service')
MAIL = Path('/data/var/mail')
sys.path.insert(0, str(BASE))
import google_service as g
import install_jobs
import youtube

EXPECTED_SCOPES = {
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/cloud-platform',
}

class Suite:
    def __init__(self):
        self.failed = 0
    def check(self, name, fn):
        try:
            detail = fn()
            print('[PASS] ' + name + ((' - ' + str(detail)) if detail not in (None, '') else ''))
        except Exception as exc:
            self.failed += 1
            print('[FAIL] ' + name + ' - ' + type(exc).__name__ + ': ' + str(exc))
    def require(self, condition, message):
        if not condition:
            raise RuntimeError(message)

def load(path):
    return json.loads(Path(path).read_text())

def sqlite_ok(path):
    with sqlite3.connect(path) as conn:
        result = conn.execute('PRAGMA integrity_check').fetchone()[0]
    if result != 'ok':
        raise RuntimeError(str(path) + ': ' + result)
    return 'integrity=ok'

def http_status(url, method='GET', headers=None):
    merged = {'User-Agent': 'MultiverseGoogleService/1.0'}; merged.update(headers or {}); request = urllib.request.Request(url, headers=merged, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()

def tcp_open(port):
    with socket.create_connection(('127.0.0.1', port), timeout=3):
        return 'listening'

def quick():
    s = Suite()
    def token():
        data = load(RUNTIME / 'oauth-token.json')
        s.require(bool(data.get('refresh_token')), 'refresh token missing')
        s.require('refresh_token_expires_in' not in data, 'Testing-mode refresh-token expiry is present')
        scopes = set(str(data.get('scope', '')).split())
        s.require(EXPECTED_SCOPES <= scopes, 'required scopes missing')
        token, expires = g.access_token()
        s.require(bool(token) and int(expires or 0) > 3000, 'access-token refresh failed or expiry too short')
        return f'production refresh token; scopes={len(scopes)}'
    s.check('Production OAuth refresh', token)
    s.check('Gmail API', lambda: 'messages=' + str(g.api_json('https://gmail.googleapis.com/gmail/v1/users/me/profile').get('messagesTotal')))
    s.check('Calendar API', lambda: 'calendars=' + str(len(g.api_json('https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=10').get('items', []))))
    s.check('Drive API', lambda: 'files=' + str(len(g.api_json('https://www.googleapis.com/drive/v3/files?pageSize=10&fields=files(id)').get('files', []))))
    def channel():
        item = youtube.own_channel(); title = item.get('snippet', {}).get('title'); handle = item.get('snippet', {}).get('customUrl')
        s.require(bool(item.get('id')), 'channel ID missing')
        return f'{title} {handle}'
    s.check('YouTube channel', channel)
    def pubsub():
        pid, _ = g.google_project(); topic = f'projects/{pid}/topics/multiverse-gmail'; sub = f'projects/{pid}/subscriptions/multiverse-gmail'
        s.require(g.api_json('https://pubsub.googleapis.com/v1/' + topic).get('name') == topic, 'topic missing')
        info = g.api_json('https://pubsub.googleapis.com/v1/' + sub)
        s.require(info.get('topic') == topic, 'subscription missing or points at wrong topic')
        policy = g.api_json('https://pubsub.googleapis.com/v1/' + topic + ':getIamPolicy')
        member = 'serviceAccount:gmail-api-push@system.gserviceaccount.com'
        s.require(any(b.get('role') == 'roles/pubsub.publisher' and member in b.get('members', []) for b in policy.get('bindings', [])), 'Gmail publisher IAM binding missing')
        return 'topic/subscription/IAM=ok'
    s.check('Gmail Pub/Sub resources', pubsub)
    def watches():
        now = int(time.time() * 1000); gmail = load(RUNTIME / 'pubsub.json'); calendar = load(RUNTIME / 'calendar-watch.json'); drive = load(RUNTIME / 'drive-watch.json')
        s.require(int(gmail.get('watch_expiration') or 0) > now + 3600000, 'Gmail watch expires too soon')
        channels = calendar.get('channels', []); s.require(bool(channels), 'Calendar watch missing')
        s.require(all(int(x.get('expiration') or 0) > now + 3600000 for x in channels), 'Calendar watch expires too soon')
        d = drive.get('channel') or {}; s.require(int(d.get('expiration') or 0) > now + 3600000, 'Drive watch expires too soon')
        return 'gmail/calendar/drive future expirations=ok'
    s.check('Push watches', watches)
    s.check('Mail gateway port', lambda: tcp_open(16201))
    s.check('OAuth SMTP bridge port', lambda: tcp_open(16202))
    s.check('Webhook gateway port', lambda: tcp_open(16301))
    def public_hook():
        code, body = http_status('https://raspi.jonnyontherun.org/hooks/google/health')
        s.require(code == 200 and b'"ok":true' in body, 'public health endpoint failed')
        return 'HTTP 200'
    s.check('Public webhook endpoint', public_hook)
    def reject():
        headers = {'X-Goog-Channel-ID': 'invalid', 'X-Goog-Channel-Token': 'invalid'}
        c1, _ = http_status('https://raspi.jonnyontherun.org/hooks/google/calendar', 'POST', headers)
        c2, _ = http_status('https://raspi.jonnyontherun.org/hooks/google/drive', 'POST', headers)
        s.require((c1, c2) == (403, 403), f'expected 403/403, got {c1}/{c2}')
        return 'forged Calendar/Drive notifications rejected'
    s.check('Webhook token rejection', reject)
    def listener():
        p = subprocess.run(['pgrep', '-f', 'google_service.py pubsub-listen'], capture_output=True, text=True)
        s.require(p.returncode == 0 and p.stdout.strip(), 'Pub/Sub listener process not running')
        return 'running'
    s.check('Pub/Sub listener process', listener)
    def schedules():
        current = set(install_jobs.current_lines()); missing = [x for x in install_jobs.jobs() if x not in current]
        s.require(not missing, str(len(missing)) + ' managed jobs missing')
        return f'{len(install_jobs.jobs())} managed jobs present'
    s.check('Scheduled jobs', schedules)
    s.check('Retired app password absent', lambda: (s.require(not (MAIL / 'secrets/gmail-app-password').exists(), 'obsolete app password exists') or 'absent'))
    def private_runtime():
        s.require(stat.S_IMODE(RUNTIME.stat().st_mode) & 0o077 == 0, 'runtime directory is group/world accessible')
        names = ('oauth-token.json', 'pubsub.json', 'calendar-watch.json', 'drive-watch.json',
                 'gmail-sync.sqlite3', 'calendar.sqlite3', 'drive.sqlite3', 'events.sqlite3',
                 'pubsub-listen.log', 'smtp-bridge.log', 'webhook-gateway.log')
        bad = []
        for name in names:
            path = RUNTIME / name
            if path.exists() and stat.S_IMODE(path.stat().st_mode) & 0o077:
                bad.append(name + ':' + oct(stat.S_IMODE(path.stat().st_mode)))
        s.require(not bad, 'group/world-readable runtime files: ' + ', '.join(bad))
        return 'runtime dir/files private'
    s.check('Runtime file permissions', private_runtime)
    for name in ('gmail-sync.sqlite3', 'calendar.sqlite3', 'drive.sqlite3', 'events.sqlite3'):
        s.check('SQLite ' + name, lambda n=name: sqlite_ok(RUNTIME / n))
    def dovecot():
        cfg = load(MAIL / 'config.json'); client = imaplib.IMAP4('127.0.0.1', cfg['imap_port'], timeout=5)
        try:
            client.login(cfg['account'], (MAIL / 'secrets/local-password').read_text().strip()); status, boxes = client.list(); s.require(status == 'OK', 'IMAP LIST failed'); return f'mailboxes={len(boxes or [])}'
        finally:
            try: client.logout()
            except Exception: pass
    s.check('Private Dovecot archive', dovecot)
    def backup_timer():
        proc = subprocess.run(['systemctl', 'is-active', 'local-mail-backup.timer'], capture_output=True, text=True)
        s.require(proc.stdout.strip() == 'active', 'backup timer is not active')
        status = load(MAIL / 'status.json'); when = int(status.get('backup_at') or 0); s.require(when and time.time() - when < 24 * 3600, 'no successful backup in last 24h')
        return 'active; recent backup present'
    s.check('Encrypted Nitro backup schedule', backup_timer)
    print(f'quick_summary=PASS' if s.failed == 0 else f'quick_summary=FAIL failures={s.failed}')
    return 0 if s.failed == 0 else 1

def run_command(name, command, timeout):
    print('[RUN] ' + name)
    result = subprocess.run(command, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(name + ' failed with exit ' + str(result.returncode))

def full():
    if quick():
        return 1
    print('[RUN] renew Gmail/Calendar/Drive watches')
    for fn in (g.gmail_watch, g.calendar_watch, g.drive_watch):
        if fn():
            return 1
    if g.calendar_push_self_test():
        return 1
    if g.drive_push_self_test():
        return 1
    if youtube.self_test_cmd(None):
        return 1
    run_command('local mail regressions', ['/usr/bin/python3', str(REPO / 'utils/mail_service/test_local.py')], 60)
    run_command('Roundcube compose/draft/reply', ['/usr/bin/python3', str(REPO / 'utils/mail_service/verify_webmail.py')], 60)
    run_command('encrypted backup/restore', ['/usr/bin/python3', str(REPO / 'utils/mail_service/verify_restore.py')], 360)
    print('[RUN] final quick health')
    return quick()

def live_mail():
    state = MAIL / 'verification/live-test.json'
    if state.exists():
        archive = state.with_name('live-test.before-' + time.strftime('%Y%m%d%H%M%S') + '.json')
        state.replace(archive)
        print('archived_previous_state=' + str(archive))
    run_command('Roundcube live send', ['/usr/bin/python3', str(REPO / 'utils/mail_service/verify_live.py'), 'send'], 90)
    run_command('Gmail push/local receipt', ['/usr/bin/python3', str(REPO / 'utils/mail_service/verify_live.py'), 'verify'], 90)
    print('mail_test=PASS; one real self-addressed test message remains by design')
    return 0

def supervisor():
    patterns = (
        '^/usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/google_service.py pubsub-listen$',
        '^/usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/gmail_smtp_bridge.py$',
        '^/usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/webhook_gateway.py$',
        '^/usr/bin/flock -n /data/var/google-service/pubsub-listen.lock ',
        '^/usr/bin/flock -n /data/var/google-service/smtp-bridge.lock ',
        '^/usr/bin/flock -n /data/var/google-service/webhook-gateway.lock ',
    )
    print('[RUN] kill persistent Google-service processes')
    for pattern in patterns:
        p = subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True)
        for raw in p.stdout.split():
            try:
                import os; os.kill(int(raw), 15)
            except (ProcessLookupError, ValueError):
                pass
    time.sleep(2)
    for port in (16202, 16301):
        try:
            tcp_open(port)
            raise RuntimeError(f'port {port} still listening immediately after kill')
        except (ConnectionRefusedError, OSError):
            pass
    print('[RUN] wait for one-minute cron supervisors')
    deadline = time.time() + 95
    while time.time() < deadline:
        try:
            tcp_open(16202); tcp_open(16301)
            p = subprocess.run(['pgrep', '-f', '^/usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/google_service.py pubsub-listen$'], capture_output=True, text=True)
            if p.returncode == 0 and p.stdout.strip():
                print('supervisor_recovery=PASS')
                return quick()
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError('managed processes did not recover within 95 seconds')

def recovery():
    run_command('live-message backup/recovery', ['/usr/bin/python3', str(REPO / 'utils/mail_service/verify_live_recovery.py')], 360)
    return 0

def main():
    parser = argparse.ArgumentParser(description='Multiverse Google-service health and integration tests')
    parser.add_argument('mode', choices=('quick', 'full', 'mail', 'recovery', 'supervisor'), nargs='?', default='quick')
    args = parser.parse_args()
    return {'quick': quick, 'full': full, 'mail': live_mail, 'recovery': recovery, 'supervisor': supervisor}[args.mode]()

if __name__ == '__main__':
    raise SystemExit(main())
