#!/usr/bin/env python3
import imaplib,json,ssl,subprocess,time
from pathlib import Path
ROOT=Path('/data/var/mail'); APP=Path('/data/src/github/utils/hpr/utils/mail_service/mail_service.py')
def trigger(): subprocess.Popen(['/usr/bin/python3',str(APP),'receive'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def main():
 while True:
  try:
   cfg=json.loads((ROOT/'config.json').read_text());pw=(ROOT/'secrets/gmail-app-password').read_text().strip()
   c=imaplib.IMAP4_SSL('imap.gmail.com',993,timeout=60,ssl_context=ssl.create_default_context());c.login(cfg['account'],pw);c.select('INBOX',readonly=True)
   while True:
    tag=c._new_tag(); c.send(tag+b' IDLE\r\n'); line=c.readline()
    if not line.startswith(b'+'): raise RuntimeError('IDLE rejected')
    c.sock.settimeout(29*60)
    try: line=c.readline()
    except TimeoutError: line=b''
    c.send(b'DONE\r\n'); c.sock.settimeout(60)
    while True:
     done=c.readline()
     if done.startswith(tag+b' '): break
    if b' EXISTS' in line or b' RECENT' in line: trigger()
  except Exception: time.sleep(10)
if __name__=='__main__': main()
