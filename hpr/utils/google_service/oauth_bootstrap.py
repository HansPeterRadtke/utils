#!/usr/bin/env python3
import base64,hashlib,json,os,secrets,sys,urllib.parse,urllib.request,urllib.error
from pathlib import Path
SECRET=Path('/data/infra/secrets/google.txt'); STATE=Path('/data/var/google-service/oauth-state.json'); MAIL_PENDING=Path('/data/var/mail/secrets/oauth-pending.json'); TOKEN=Path('/data/var/google-service/oauth-token.json')
SCOPES=['https://www.googleapis.com/auth/gmail.modify','https://www.googleapis.com/auth/gmail.send','https://www.googleapis.com/auth/calendar','https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/youtube.upload','https://www.googleapis.com/auth/youtube']
def cfg():
 d={}
 for line in SECRET.read_text().splitlines():
  if ':' in line:
   k,v=line.split(':',1);d[k.strip()]=v.strip()
 return d
def start():
 c=cfg(); verifier=secrets.token_urlsafe(64); challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode(); state=secrets.token_urlsafe(32)
 STATE.write_text(json.dumps({'verifier':verifier,'state':state})+'\n');os.chmod(STATE,0o600)
 q={'client_id':c['clientid'],'redirect_uri':'http://localhost','response_type':'code','scope':' '.join(SCOPES),'access_type':'offline','prompt':'consent','include_granted_scopes':'true','state':state,'code_challenge':challenge,'code_challenge_method':'S256'}
 print('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode(q))

def cleanup_callback():
 text=SECRET.read_text();lines=[];removed=0
 for line in text.splitlines():
  if ('http://localhost' in line or 'https://localhost' in line) and 'code=' in line:
   removed+=1;continue
  lines.append(line)
 SECRET.write_text('\n'.join(lines).rstrip()+'\n');os.chmod(SECRET,0o600);print('oauth_callback_cleanup=OK removed='+str(removed));return 0

def finish(url=None):
 c=cfg()
 if url is None:
  text=SECRET.read_text()
  urls=[]
  for line in text.splitlines():
   for prefix in ('http://localhost','https://localhost'):
    i=line.find(prefix)
    if i>=0: urls.append(line[i:].strip())
  if not urls: raise SystemExit('No callback URL in google.txt')
  url=urls[-1]
 q=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
 callback_state=q.get('state',[''])[0]
 pending_path=None; st=None
 for candidate in (STATE,MAIL_PENDING):
  if candidate.exists():
   d=json.loads(candidate.read_text())
   if d.get('state')==callback_state: pending_path=candidate;st=d;break
 if st is None: raise SystemExit('OAuth state mismatch')
 code=q.get('code',[''])[0]
 if not code: raise SystemExit('No authorization code in callback URL')
 data=urllib.parse.urlencode({'client_id':c['clientid'],'client_secret':c['clientSecret'],'code':code,'code_verifier':st['verifier'],'grant_type':'authorization_code','redirect_uri':'http://localhost'}).encode()
 req=urllib.request.Request('https://oauth2.googleapis.com/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded'})
 try:
  tok=json.loads(urllib.request.urlopen(req,timeout=30).read())
 except urllib.error.HTTPError as e:
  try: err=json.loads(e.read().decode())
  except Exception: err={}
  raise SystemExit('token exchange failed: '+str(err.get('error','http_'+str(e.code)))+' - '+str(err.get('error_description','')))
 TOKEN.parent.mkdir(parents=True,exist_ok=True);TOKEN.write_text(json.dumps(tok,indent=2)+'\n');os.chmod(TOKEN,0o600); pending_path.unlink(missing_ok=True)
 print('refresh_token_present',bool(tok.get('refresh_token')));print('scope_count',len(tok.get('scope','').split()))
if __name__=='__main__':
 if len(sys.argv)==1 or sys.argv[1]=='start': start()
 elif sys.argv[1]=='finish': finish(sys.argv[2] if len(sys.argv)==3 else None)
 elif sys.argv[1]=='cleanup-callback': cleanup_callback()
 else: raise SystemExit('usage: oauth_bootstrap.py start | finish [CALLBACK_URL] | cleanup-callback')
