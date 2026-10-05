#!/usr/bin/env python3
import http.server,json,hmac,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/data/src/github/utils/hpr/utils/google_service')
from event_bus import emit
ROOT=Path('/data/var/google-service')
SYNC={
 'calendar':['/usr/bin/flock','-n',str(ROOT/'calendar-sync.lock'),'/usr/bin/python3','/data/src/github/utils/hpr/utils/google_service/google_service.py','calendar-sync'],
 'drive':['/usr/bin/flock','-n',str(ROOT/'drive-sync.lock'),'/usr/bin/python3','/data/src/github/utils/hpr/utils/google_service/google_service.py','drive-sync'],
}
FILES={'calendar':ROOT/'calendar-watch.json','drive':ROOT/'drive-watch.json'}
def channels(kind):
 p=FILES[kind]
 if not p.exists():return []
 try:d=json.loads(p.read_text())
 except Exception:return []
 return d.get('channels',[]) if kind=='calendar' else ([d.get('channel')] if d.get('channel') else [])
def match(kind,cid,token):
 for ch in channels(kind):
  if ch and ch.get('id')==cid and hmac.compare_digest(str(ch.get('token','')),str(token or '')):return ch
 return None
class H(http.server.BaseHTTPRequestHandler):
 server_version='MultiverseHooks';sys_version=''
 def log_message(self,*a):pass
 def send_empty(self,code):
  self.send_response(code);self.send_header('Content-Length','0');self.send_header('Cache-Control','no-store');self.end_headers()
 def do_GET(self):
  if self.path.rstrip('/')=='/hooks/google/health':
   b=b'{"ok":true}';self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
  else:self.send_empty(404)
 def do_POST(self):
  parts=self.path.split('?',1)[0].rstrip('/').split('/')
  if len(parts)!=4 or parts[:3]!=['','hooks','google'] or parts[3] not in ('calendar','drive'):
   self.send_empty(404);return
  kind=parts[3];cid=self.headers.get('X-Goog-Channel-ID','');token=self.headers.get('X-Goog-Channel-Token','');ch=match(kind,cid,token)
  if not ch:self.send_empty(403);return
  n=int(self.headers.get('Content-Length','0') or 0)
  if n:self.rfile.read(min(n,65536))
  self.send_empty(200)
  data={'channel_id':cid,'resource_id':self.headers.get('X-Goog-Resource-ID'),'resource_state':self.headers.get('X-Goog-Resource-State'),'resource_uri':self.headers.get('X-Goog-Resource-URI'),'message_number':self.headers.get('X-Goog-Message-Number'),'changed':self.headers.get('X-Goog-Changed'),'expiration':self.headers.get('X-Goog-Channel-Expiration')}
  subject=ch.get('calendar_id') if kind=='calendar' else 'drive'
  emit('//google/'+kind+'/'+str(data.get('resource_id') or cid),'com.google.'+kind+'.change',subject,data,event_id='google:'+kind+':'+cid+':'+str(data.get('message_number') or '0'))
  subprocess.Popen(SYNC[kind],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
if __name__=='__main__':http.server.ThreadingHTTPServer(('127.0.0.1',16301),H).serve_forever()
