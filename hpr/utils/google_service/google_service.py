#!/usr/bin/env python3
import json,urllib.parse,urllib.request,urllib.error,sys,time,base64,email,sqlite3,socket,email.message,uuid
from event_bus import emit as emit_event
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

def token_info():
 a,_=access_token();r=json.loads(urllib.request.urlopen('https://oauth2.googleapis.com/tokeninfo?access_token='+urllib.parse.quote(a),timeout=20).read());print('token_info=OK audience_present='+str(bool(r.get('aud')))+' scopes='+str(len(r.get('scope','').split()))+' expires_in='+str(r.get('expires_in')));return 0
def gmail_profile():
 p=api_json('https://gmail.googleapis.com/gmail/v1/users/me/profile');print('gmail_profile=OK messages='+str(p.get('messagesTotal'))+' threads='+str(p.get('threadsTotal'))+' history='+str(p.get('historyId')));return 0
def gmail_recent():
 r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=10');print('gmail_recent=OK count='+str(len(r.get('messages',[]))));return 0
def calendar_sync():
 db=Path('/data/var/google-service/calendar.sqlite3');con=sqlite3.connect(db);con.execute('create table if not exists calendars(id text primary key, summary text, sync_token text, json text, synced_at integer)');con.execute('create table if not exists events(calendar_id text, id text, json text, primary key(calendar_id,id))')
 calendars=[];pt=None
 while True:
  q={'maxResults':250}
  if pt:q['pageToken']=pt
  r=api_json('https://www.googleapis.com/calendar/v3/users/me/calendarList?'+urllib.parse.urlencode(q));calendars+=r.get('items',[]);pt=r.get('nextPageToken')
  if not pt:break
 changed=0
 for cal in calendars:
  cid=cal['id'];row=con.execute('select sync_token from calendars where id=?',(cid,)).fetchone();token=row[0] if row else None
  def run(tok):
   nonlocal changed
   page=None;final=None
   while True:
    q={'showDeleted':'true','maxResults':2500}
    if tok:q['syncToken']=tok
    if page:q['pageToken']=page
    url='https://www.googleapis.com/calendar/v3/calendars/'+urllib.parse.quote(cid,safe='')+'/events?'+urllib.parse.urlencode(q)
    rr=api_json(url)
    for ev in rr.get('items',[]):
     if ev.get('status')=='cancelled':con.execute('delete from events where calendar_id=? and id=?',(cid,ev['id']))
     else:con.execute('insert or replace into events(calendar_id,id,json) values(?,?,?)',(cid,ev['id'],json.dumps(ev,separators=(',',':'))))
     changed+=1
    page=rr.get('nextPageToken');final=rr.get('nextSyncToken') or final
    if not page:return final
  try:newtok=run(token)
  except urllib.error.HTTPError as e:
   if e.code!=410:raise
   con.execute('delete from events where calendar_id=?',(cid,));newtok=run(None)
  con.execute('insert or replace into calendars(id,summary,sync_token,json,synced_at) values(?,?,?,?,?)',(cid,cal.get('summary'),newtok,json.dumps(cal,separators=(',',':')),int(time.time())))
 con.commit();counts=con.execute('select count(*) from events').fetchone()[0];con.close();db.chmod(0o600);print('calendar_sync=OK calendars='+str(len(calendars))+' events='+str(counts)+' changes='+str(changed));return 0

def drive_sync():
 db=Path('/data/var/google-service/drive.sqlite3');con=sqlite3.connect(db);con.execute('create table if not exists files(id text primary key,json text)');con.execute('create table if not exists state(key text primary key,value text)');row=con.execute("select value from state where key='page_token'").fetchone();token=row[0] if row else None;changed=0
 if token is None:
  pt=None
  while True:
   q={'pageSize':1000,'fields':'nextPageToken,files(id,name,mimeType,modifiedTime,parents,trashed,size,md5Checksum,webViewLink)'}
   if pt:q['pageToken']=pt
   r=api_json('https://www.googleapis.com/drive/v3/files?'+urllib.parse.urlencode(q))
   for f in r.get('files',[]):con.execute('insert or replace into files(id,json) values(?,?)',(f['id'],json.dumps(f,separators=(',',':'))));changed+=1
   pt=r.get('nextPageToken')
   if not pt:break
  token=api_json('https://www.googleapis.com/drive/v3/changes/startPageToken')['startPageToken']
 else:
  pt=token;newstart=None
  while True:
   q={'pageToken':pt,'pageSize':1000,'includeRemoved':'true','fields':'nextPageToken,newStartPageToken,changes(fileId,removed,file(id,name,mimeType,modifiedTime,parents,trashed,size,md5Checksum,webViewLink))'}
   r=api_json('https://www.googleapis.com/drive/v3/changes?'+urllib.parse.urlencode(q))
   for ch in r.get('changes',[]):
    if ch.get('removed'):con.execute('delete from files where id=?',(ch['fileId'],))
    elif ch.get('file'):con.execute('insert or replace into files(id,json) values(?,?)',(ch['fileId'],json.dumps(ch['file'],separators=(',',':'))))
    changed+=1
   if r.get('nextPageToken'):pt=r['nextPageToken'];continue
   newstart=r.get('newStartPageToken') or pt;token=newstart;break
 con.execute("insert or replace into state(key,value) values('page_token',?)",(token,));con.commit();count=con.execute('select count(*) from files').fetchone()[0];con.close();db.chmod(0o600);print('drive_sync=OK files='+str(count)+' changes='+str(changed));return 0

def calendar_check():
 r=api_json('https://www.googleapis.com/calendar/v3/users/me/calendarList?maxResults=10');print('calendar_list=OK count='+str(len(r.get('items',[]))));return 0
def drive_check():
 r=api_json('https://www.googleapis.com/drive/v3/files?pageSize=10&fields=files(id,name,mimeType)');print('drive_list=OK count='+str(len(r.get('files',[]))));return 0
def youtube_check():
 r=api_json('https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true');print('youtube_channels=OK count='+str(len(r.get('items',[]))));return 0




def pubsub_probe():
 try:
  status,body=call('https://pubsub.googleapis.com/v1/projects/809990734271/topics?pageSize=1');print('pubsub_probe=OK status='+str(status)+' bytes='+str(len(body)));return 0
 except urllib.error.HTTPError as e:
  data=e.read().decode(errors='ignore');
  try: err=json.loads(data).get('error',{});print('pubsub_probe=HTTP'+str(e.code)+' status='+str(err.get('status'))+' reason='+str((err.get('details') or [{}])[0].get('reason','')))
  except Exception: print('pubsub_probe=HTTP'+str(e.code))
  return 1

def gmail_send_self_test():
 msg=email.message.EmailMessage();msg['From']='multiverse3dhpr@gmail.com';msg['To']='multiverse3dhpr@gmail.com';msg['Subject']='OAuth API self-test '+str(uuid.uuid4())[:8];msg.set_content('Multiverse Services Gmail OAuth send verification.')
 raw=base64.urlsafe_b64encode(msg.as_bytes()).rstrip(b'=').decode();r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/send','POST',{'raw':raw});print('gmail_send_self_test=OK id_present='+str(bool(r.get('id'))));return 0

def gmail_raw_dryrun():
 r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=100')
 total=0;rawbytes=0
 for item in r.get('messages',[]):
  m=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+item['id']+'?format=raw')
  raw=base64.urlsafe_b64decode(m['raw']+'='*((4-len(m['raw'])%4)%4));email.message_from_bytes(raw);total+=1;rawbytes+=len(raw)
 print('gmail_raw_dryrun=OK messages='+str(total)+' bytes='+str(rawbytes));return 0


def gmail_message_ids():
 out=[];token=None
 while True:
  q={'maxResults':500}
  if token:q['pageToken']=token
  r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?'+urllib.parse.urlencode(q))
  out.extend(x['id'] for x in r.get('messages',[]));token=r.get('nextPageToken')
  if not token:return out

def gmail_local_folder(labels):
 labels=set(labels or [])
 if 'INBOX' in labels:return 'INBOX'
 if 'TRASH' in labels:return 'Trash'
 if 'SPAM' in labels:return 'Junk'
 if 'DRAFT' in labels:return 'Drafts'
 if 'SENT' in labels:return 'Sent'
 return 'Archive'

def google_project():
 r=api_json('https://cloudresourcemanager.googleapis.com/v3/projects/809990734271')
 pid=r.get('projectId');num=str(r.get('name','')).split('/')[-1]
 if not pid:raise RuntimeError('Google Cloud project ID unavailable')
 return pid,num

def service_enable(name):
 _,num=google_project();url='https://serviceusage.googleapis.com/v1/projects/'+num+'/services/'+name+':enable'
 op=api_json(url,'POST',{})
 opn=op.get('name')
 if not opn:return
 for _ in range(60):
  time.sleep(1);x=api_json('https://serviceusage.googleapis.com/v1/'+opn)
  if x.get('done'):
   if x.get('error'):raise RuntimeError('service enable failed: '+str(x['error'].get('message','')))
   return
 raise RuntimeError('service enable timed out')

def pubsub_setup():
 service_enable('pubsub.googleapis.com');pid,_=google_project();topic='projects/'+pid+'/topics/multiverse-gmail';sub='projects/'+pid+'/subscriptions/multiverse-gmail'
 def put(url,payload):
  try:return api_json(url,'PUT',payload)
  except urllib.error.HTTPError as e:
   if e.code==409:return {}
   raise
 put('https://pubsub.googleapis.com/v1/'+topic,{})
 policy=api_json('https://pubsub.googleapis.com/v1/'+topic+':getIamPolicy','POST',{})
 member='serviceAccount:gmail-api-push@system.gserviceaccount.com';binding=next((b for b in policy.get('bindings',[]) if b.get('role')=='roles/pubsub.publisher'),None)
 if binding is None:binding={'role':'roles/pubsub.publisher','members':[]};policy.setdefault('bindings',[]).append(binding)
 if member not in binding['members']:binding['members'].append(member);api_json('https://pubsub.googleapis.com/v1/'+topic+':setIamPolicy','POST',{'policy':policy})
 put('https://pubsub.googleapis.com/v1/'+sub,{'topic':topic,'ackDeadlineSeconds':60})
 state={'project_id':pid,'topic':topic,'subscription':sub};q=Path('/data/var/google-service/pubsub.json');q.write_text(json.dumps(state,indent=2)+'\n');q.chmod(0o600)
 print('pubsub_setup=OK project='+pid+' topic=multiverse-gmail subscription=multiverse-gmail');return 0

def gmail_watch():
 st=json.loads(Path('/data/var/google-service/pubsub.json').read_text());r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/watch','POST',{'topicName':st['topic'],'labelIds':['INBOX'],'labelFilterBehavior':'INCLUDE'});st['historyId']=r.get('historyId');st['watch_expiration']=r.get('expiration');st['watch_updated']=int(time.time());p=Path('/data/var/google-service/pubsub.json');p.write_text(json.dumps(st,indent=2)+'\n');p.chmod(0o600);print('gmail_watch=OK history_present='+str(bool(st['historyId']))+' expiration_present='+str(bool(st['watch_expiration'])));return 0

def pubsub_pull_once():
 st=json.loads(Path('/data/var/google-service/pubsub.json').read_text());url='https://pubsub.googleapis.com/v1/'+st['subscription']+':pull';r=api_json(url,'POST',{'maxMessages':10,'returnImmediately':False});msgs=r.get('receivedMessages',[])
 if not msgs:print('pubsub_pull=OK messages=0');return 0
 for x in msgs:
  m=x.get('message',{});raw=m.get('data','');payload={}
  if raw:
   try:payload=json.loads(base64.b64decode(raw+'='*((4-len(raw)%4)%4)).decode())
   except Exception:payload={'decode_error':True}
  emit_event('//google/pubsub/'+st['subscription'],'com.google.gmail.change','multiverse3dhpr@gmail.com',payload,event_id='pubsub:'+str(m.get('messageId') or uuid.uuid4()))
 gmail_sync();acks=[x['ackId'] for x in msgs if x.get('ackId')]
 if acks:api_json('https://pubsub.googleapis.com/v1/'+st['subscription']+':acknowledge','POST',{'ackIds':acks})
 print('pubsub_pull=OK messages='+str(len(msgs))+' synced=yes');return 0

def pubsub_listen():
 print('pubsub_listen=START',flush=True)
 while True:
  try:pubsub_pull_once()
  except Exception as e:print('pubsub_listen_error='+type(e).__name__,flush=True);time.sleep(5)

def gmail_sync_bootstrap():
 db=Path('/data/var/google-service/gmail-sync.sqlite3');db.parent.mkdir(parents=True,exist_ok=True);con=sqlite3.connect(db);con.execute('create table if not exists messages(id text primary key, seen_at integer not null)');r=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=500');now=int(time.time());n=0
 for item in r.get('messages',[]):
  before=con.total_changes;con.execute('insert or ignore into messages(id,seen_at) values(?,?)',(item['id'],now));n+=con.total_changes-before
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
def lmtp_deliver_folder(raw,folder):
 recipient='multiverse3dhpr@gmail.com' if folder=='INBOX' else 'multiverse3dhpr+'+folder+'@gmail.com'
 sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(20);sock.connect('/data/var/mail/run/lmtp');f=sock.makefile('rwb',buffering=0)
 def recv():
  lines=[]
  while True:
   line=f.readline()
   if not line:raise RuntimeError('LMTP closed')
   lines.append(line)
   if len(line)<4 or line[3:4]!=b'-':return lines
 def send(line):f.write(line+b'\r\n');return recv()
 recv();send(b'LHLO localhost');send(b'MAIL FROM:<>');send(('RCPT TO:<'+recipient+'>').encode());send(b'DATA')
 data=raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n').replace(b'\n',b'\r\n');data=b'\r\n'.join((b'.'+x if x.startswith(b'.') else x) for x in data.split(b'\r\n'));f.write(data+b'\r\n.\r\n');reply=recv();send(b'QUIT');sock.close()
 if not reply or not reply[-1].startswith(b'2'):raise RuntimeError('LMTP delivery rejected')

def gmail_sync():
 db=Path('/data/var/google-service/gmail-sync.sqlite3');con=sqlite3.connect(db);con.execute('create table if not exists messages(id text primary key, seen_at integer not null, folder text)');
 try:con.execute('alter table messages add column folder text')
 except sqlite3.OperationalError:pass
 delivered=0
 for mid in reversed(gmail_message_ids()):
  if con.execute('select 1 from messages where id=?',(mid,)).fetchone():continue
  m=api_json('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+mid+'?format=raw');raw=base64.urlsafe_b64decode(m['raw']+'='*((4-len(m['raw'])%4)%4));folder=gmail_local_folder(m.get('labelIds'));lmtp_deliver_folder(raw,folder);con.execute('insert into messages(id,seen_at,folder) values(?,?,?)',(mid,int(time.time()),folder));con.commit();delivered+=1
 con.close();print('gmail_sync=OK delivered='+str(delivered));return 0

if __name__=='__main__':
 if len(sys.argv)==2:
  actions={'token-info':token_info,'check':check,'gmail-profile':gmail_profile,'gmail-recent':gmail_recent,'calendar-check':calendar_check,'calendar-sync':calendar_sync,'drive-check':drive_check,'drive-sync':drive_sync,'youtube-check':youtube_check,'pubsub-probe':pubsub_probe,'pubsub-setup':pubsub_setup,'gmail-watch':gmail_watch,'pubsub-pull-once':pubsub_pull_once,'pubsub-listen':pubsub_listen,'gmail-send-self-test':gmail_send_self_test,'gmail-raw-dryrun':gmail_raw_dryrun,'gmail-sync-bootstrap':gmail_sync_bootstrap,'gmail-sync':gmail_sync}
  if sys.argv[1] in actions: raise SystemExit(actions[sys.argv[1]]())
 raise SystemExit('usage: google_service.py check|gmail-profile|gmail-recent|calendar-check|calendar-sync|drive-check|drive-sync|youtube-check|pubsub-probe|pubsub-setup|gmail-watch|pubsub-pull-once|pubsub-listen|gmail-send-self-test|gmail-raw-dryrun|gmail-sync-bootstrap|gmail-sync')
