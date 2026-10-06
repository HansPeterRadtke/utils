#!/usr/bin/env python3
import os
import json,sqlite3,uuid,datetime,sys
from pathlib import Path
os.umask(0o077)
DB=Path('/data/var/google-service/events.sqlite3')
def init():
 DB.parent.mkdir(parents=True,exist_ok=True);con=sqlite3.connect(DB);con.execute('create table if not exists events(id text primary key,specversion text not null,source text not null,type text not null,subject text,time text not null,datacontenttype text,data text not null,created_at integer not null)');con.commit();con.close();DB.chmod(0o600)
def emit(source,type_,subject=None,data=None,event_id=None):
 init();ev={'specversion':'1.0','id':event_id or str(uuid.uuid4()),'source':source,'type':type_,'time':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'datacontenttype':'application/json','data':data or {}}
 if subject is not None:ev['subject']=subject
 con=sqlite3.connect(DB);con.execute('insert or ignore into events(id,specversion,source,type,subject,time,datacontenttype,data,created_at) values(?,?,?,?,?,?,?,?,strftime("%s","now"))',(ev['id'],ev['specversion'],ev['source'],ev['type'],ev.get('subject'),ev['time'],ev['datacontenttype'],json.dumps(ev['data'],separators=(',',':'))));con.commit();con.close();return ev
def recent(limit=10):
 init();con=sqlite3.connect(DB);rows=con.execute('select id,source,type,subject,time,data from events order by created_at desc,rowid desc limit ?',(limit,)).fetchall();con.close();return [{'id':a,'source':b,'type':c,'subject':d,'time':e,'data':json.loads(f)} for a,b,c,d,e,f in rows]
if __name__=='__main__':
 if len(sys.argv)>=2 and sys.argv[1]=='recent':
  for x in recent(int(sys.argv[2]) if len(sys.argv)>2 else 10):print(json.dumps(x,separators=(',',':')))
 else:raise SystemExit('usage: event_bus.py recent [N]')
