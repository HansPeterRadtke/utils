#!/usr/bin/env python3
import imaplib,ssl,subprocess,time,sys
from pathlib import Path
sys.path.insert(0,'/data/src/github/utils/hpr/utils/google_service')
from google_service import access_token
ACCOUNT='multiverse3dhpr@gmail.com'
SYNC=['/usr/bin/python3','/data/src/github/utils/hpr/utils/google_service/google_service.py','gmail-sync']

def xoauth2(client):
    token,_=access_token()
    auth=f'user={ACCOUNT}\x01auth=Bearer {token}\x01\x01'.encode()
    client.authenticate('XOAUTH2',lambda _: auth)

def sync():
    subprocess.run(SYNC,check=False,timeout=900,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def idle_once(client,seconds=25*60):
    tag=client._new_tag();client.send(tag+b' IDLE\r\n');line=client.readline()
    if not line.startswith(b'+'): raise RuntimeError('Gmail rejected IDLE')
    client.sock.settimeout(seconds)
    changed=False
    try:
        while True:
            line=client.readline()
            if not line: raise RuntimeError('Gmail closed IDLE connection')
            if b' EXISTS' in line or b' RECENT' in line or b' EXPUNGE' in line:
                changed=True;break
    except TimeoutError:
        pass
    finally:
        client.send(b'DONE\r\n');client.sock.settimeout(60)
        while True:
            line=client.readline()
            if line.startswith(tag+b' '): break
    return changed

def run(once=False):
    while True:
        try:
            with imaplib.IMAP4_SSL('imap.gmail.com',993,timeout=60,ssl_context=ssl.create_default_context()) as c:
                xoauth2(c);c.select('INBOX',readonly=True)
                while True:
                    changed=idle_once(c,60 if once else 25*60)
                    if changed: sync()
                    if once:return 0
                    c.noop()
        except Exception as e:
            if once: print(type(e).__name__+': '+str(e));return 1
            time.sleep(10)
if __name__=='__main__': raise SystemExit(run('--once' in sys.argv))
