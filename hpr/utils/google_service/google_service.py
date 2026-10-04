#!/usr/bin/env python3
import json,urllib.parse,urllib.request,urllib.error,sys,time,base64,email,sqlite3,socket
from pathlib import Path
SECRET=Path('/data/infra/secrets/google.txt');TOKEN=Path('/data/var/google-service/oauth-token.json')
def config():
 d={}
 for line in SECRET.read_text().splitlines():
  if ':' in line:
   k,v=line.split(':',1);d[k.strip()]=v.strip()
 return d
def access_token():
 c=config();t=json.loads(TOKEN.read_text());data=urllib.parse.urlencode({'client_id':c['clientid'],'client_secret':c['clientSecret'],'refresh_token':t['refresh_token'],'grant_type':'refresh_token'}).encode();r=json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=data),timeout=20).read());return r['access_token'],r.get('expires_in')
def call(url):
 a,_=access_token();req=urllib.request.Request(url,headers={'Authorization':'Bearer '+a});res=urllib.request.urlopen(req,timeout=20);return res.status,res.read()
def gmail_profile():
 status,body=call('https://gmail.googleapis.com/gmail/v1/users/me/profile');d=json.loads(body);print('gmail_profile','OK',status,'messages',d.get('messagesTotal'),'threads',d.get('threadsTotal'),'history_present',bool(d.get('historyId')));return 0
def gmail_labels():
 status,body=call('https://gmail.googleapis.com/gmail/v1/users/me/labels');d=json.loads(body);print('gmail_labels','OK',status,'count',len(d.get('labels',[])));return 0
def gmail_recent():
 status,body=call('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=5');d=json.loads(body);print('gmail_recent','OK',status,'returned',len(d.get('messages',[])),'estimate',d.get('resultSizeEstimate'));return 0
def check():
 tests=[('gmail','https://gmail.googleapis.com/gmail/v1/users/me/profile'),('calendar','https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=1'),('drive','https://www.googleapis.com/drive/v3/files?pageSize=1&fields=files(id,name)'),('youtube','https://www.googleapis.com/youtube/v3/channels?part=id&mine=true')]
 ok=True
 for name,url in tests:
  try: status,body=call(url);print(name,'OK',status,'bytes',len(body))
  except urllib.error.HTTPError as e: print(name,'HTTP',e.code);ok=False
 a,exp=access_token();print('refresh','OK','expires_in',exp);return 0 if ok else 1

def api_json(url,method='GET',payload=None):
 a,_=access_token();headers={'Authorization':'Bearer '+a};data=None
 if payload is not None: data=json.dumps(payload).encode();headers['Content-Type']='application/json'
 req=urllib.request.Request(url,data=data,headers=headers,method=method);return json.loads(urllib.request.urlopen(req,timeout=30).read() or b'{}')
def gmail_profile():
 p=api_json('https://gmail.googleapis.com/gmail/v1/users/me/profile');print('gmail_profile=OK messages='+str(p.get('messagesTotal'))+' threads='+str(p.get('threadsTotal'))+' history='+str(p.get('historyId')));return 0
def gmail_recent():
 r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10');print('gmail_recent=OK count='+str(len(r.get('messages',[]))));return 0
def calendar_check():
 r=api_json('https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=10');print('calendar_list=OK count='+str(len(r.get('items',[]))));return 0
def drive_check():
 r=api_json('https://www.googleapis.com/drive/v3/files?pageSize=10&fields=files(id,name,mimeType)');print('drive_list=OK count='+str(len(r.get('files',[]))));return 0
def youtube_check():
 r=api_json('https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true');print('youtube_channels=OK count='+str(len(r.get('items',[]))));return 0


def gmail_raw_dryrun():
 r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=100')
 total=0;rawbytes=0
 for item in r.get('messages',[]):
  m=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+item['id']+'?format=raw')
  raw=base64.urlsafe_b64decode(m['raw']+'='*((4-len(m['raw'])%4)%4));email.message_from_bytes(raw);total+=1;rawbytes+=len(raw)
 print('gmail_raw_dryrun=OK messages='+str(total)+' bytes='+str(rawbytes));return 0


def gmail_sync_bootstrap():
 db=Path('/data/var/google-service/gmail-sync.sqlite3');db.parent.mkdir(parents=True,exist_ok=True);con=sqlite3.connect(db);con.execute('create table if not exists messages(id text primary key, seen_at integer not null)');r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=500');now=int(time.time());n=0
 for item in r.get('messages',[]): con.execute('insert or ignore into messages(id,seen_at) values(?,?)',(item['id'],now));n+=con.total_changes
 con.commit();con.close();db.chmod(0o600);print('gmail_sync_bootstrap=OK recorded='+str(n));return 0


def lmtp_deliver(raw):
 sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(20);sock.connect('/data/var/mail/run/lmtp');f=sock.makefile('rwb',buffering=0)
 def recv():
  lines=[]
  while True:
   line=f.readline();
   if not line: raise RuntimeError('LMTP closed')
   lines.append(line)
   if len(line)<4 or line[3:4]!=b'-': return lines
 def send(line): f.write(line+b'\r\n');return recv()
 recv();send(b'LHLO localhost');send(b'MAIL FROM:<>');send(b'RCPT TO:<multiverse3dhpr@gmail.com>');send(b'DATA')
 data=raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n').replace(b'\n',b'\r\n');data=b'\r\n'.join((b'.'+x if x.startswith(b'.') else x) for x in data.split(b'\r\n'));f.write(data+b'\r\n.\r\n');reply=recv();send(b'QUIT');sock.close()
 if not reply or not reply[-1].startswith(b'2'): raise RuntimeError('LMTP delivery rejected')
def gmail_sync():
 db=Path('/data/var/google-service/gmail-sync.sqlite3');con=sqlite3.connect(db);con.execute('create table if not exists messages(id text primary key, seen_at integer not null)');r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=500');delivered=0
 for item in reversed(r.get('messages',[])):
  mid=item['id']
  if con.execute('select 1 from messages where id=?',(mid,)).fetchone(): continue
  m=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+mid+'?format=raw');raw=base64.urlsafe_b64decode(m['raw']+'='*((4-len(m['raw'])%4)%4));lmtp_deliver(raw);con.execute('insert into messages(id,seen_at) values(?,?)',(mid,int(time.time())));con.commit();delivered+=1
 con.close();print('gmail_sync=OK delivered='+str(delivered));return 0

if __name__=='__main__':
 if len(sys.argv)==2:
  actions={'check':check,'gmail-profile':gmail_profile,'gmail-recent':gmail_recent,'calendar-check':calendar_check,'drive-check':drive_check,'youtube-check':youtube_check,'gmail-raw-dryrun':gmail_raw_dryrun,'gmail-sync-bootstrap':gmail_sync_bootstrap,'gmail-sync':gmail_sync}
  if sys.argv[1] in actions: raise SystemExit(actions[sys.argv[1]]())
 raise SystemExit('usage: google_service.py check|gmail-profile|gmail-labels|gmail-recent|calendar-check|drive-check|youtube-check|gmail-raw-dryrun')
