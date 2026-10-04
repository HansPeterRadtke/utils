#!/usr/bin/env python3
import json,subprocess,time,sqlite3,os
from pathlib import Path
ROOT=Path('/data/var/google-service'); ROOT.mkdir(parents=True,exist_ok=True)
STATUS=ROOT/'cloud-setup-status.json'; LOG=ROOT/'cloud-setup.log'
BASE=['/usr/bin/python3','/data/src/github/utils/hpr/utils/google_service/google_service.py']
OAUTH=['/usr/bin/python3','/data/src/github/utils/hpr/utils/google_service/oauth_bootstrap.py']
def status(state,**kw):
 d={'state':state,'updated':int(time.time()),**kw};STATUS.write_text(json.dumps(d,indent=2)+'\n');STATUS.chmod(0o600)
def run(cmd,timeout=180):
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
 with LOG.open('a') as f:f.write('$ '+' '.join(cmd)+'\n'+p.stdout+p.stderr+'\n')
 return p
def install_cron():
 p=subprocess.run(['crontab','-l'],capture_output=True,text=True);lines=[x for x in p.stdout.splitlines() if 'multiverse-google-gmail-watch' not in x and 'multiverse-google-pubsub-listen' not in x]
 lines.append('13 3 * * * /usr/bin/flock -n /data/var/google-service/gmail-watch.lock /usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/google_service.py gmail-watch >/dev/null 2>&1 # multiverse-google-gmail-watch')
 lines.append('@reboot /usr/bin/flock -n /data/var/google-service/pubsub-listen.lock /usr/bin/python3 /data/src/github/utils/hpr/utils/google_service/google_service.py pubsub-listen >>/data/var/google-service/pubsub-listen.log 2>&1 # multiverse-google-pubsub-listen')
 q=subprocess.run(['crontab','-'],input='\n'.join(lines)+'\n',text=True);return q.returncode==0
def main():
 status('WAITING_FOR_CALLBACK')
 deadline=time.time()+3600
 while time.time()<deadline:
  p=run(OAUTH+['finish'],60)
  if p.returncode==0:break
  if 'No callback URL' not in (p.stdout+p.stderr) and 'OAuth state mismatch' not in (p.stdout+p.stderr):status('OAUTH_FAILED',detail=(p.stdout+p.stderr)[-400:]);return 2
  time.sleep(2)
 else:status('TIMED_OUT_WAITING_FOR_CALLBACK');return 3
 run(OAUTH+['cleanup-callback'],30)
 p=run(BASE+['pubsub-setup'],180)
 if p.returncode:status('PUBSUB_SETUP_FAILED',detail=(p.stdout+p.stderr)[-500:]);return 4
 p=run(BASE+['gmail-watch'],60)
 if p.returncode:status('GMAIL_WATCH_FAILED',detail=(p.stdout+p.stderr)[-500:]);return 5
 if not install_cron():status('CRON_FAILED');return 6
 listener=subprocess.Popen(['/usr/bin/flock','-n',str(ROOT/'pubsub-listen.lock')]+BASE+['pubsub-listen'],stdout=(ROOT/'pubsub-listen.log').open('ab'),stderr=subprocess.STDOUT,start_new_session=True)
 time.sleep(2)
 before=0
 edb=ROOT/'events.sqlite3'
 if edb.exists():
  try:
   c=sqlite3.connect(edb);before=c.execute('select count(*) from events').fetchone()[0];c.close()
  except Exception:pass
 send=run(BASE+['gmail-send-self-test'],60)
 if send.returncode:status('SEND_TEST_FAILED',detail=(send.stdout+send.stderr)[-500:]);return 7
 deadline=time.time()+60;after=before
 while time.time()<deadline:
  time.sleep(2)
  if edb.exists():
   try:
    c=sqlite3.connect(edb);after=c.execute('select count(*) from events').fetchone()[0];c.close()
   except Exception:pass
  if after>before:break
 status('READY',event_before=before,event_after=after,push_event_seen=after>before,listener_pid=listener.pid)
 return 0
if __name__=='__main__':raise SystemExit(main())
