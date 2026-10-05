#!/usr/bin/env python3
import asyncio,sys
sys.path.insert(0,'/data/src/github/utils/hpr/utils/google_service')
from google_service import gmail_send_raw
HOST='127.0.0.1';PORT=16202;MAX=30*1024*1024
async def reply(w,s):w.write((s+'\r\n').encode());await w.drain()
async def handle(r,w):
 peer=w.get_extra_info('peername')
 if not peer or peer[0] not in ('127.0.0.1','::1'):
  w.close();await w.wait_closed();return
 await reply(w,'220 localhost Multiverse OAuth SMTP bridge')
 mail=False;rcpts=[]
 try:
  while True:
   line=await r.readline()
   if not line:break
   text=line.decode('utf-8','replace').rstrip('\r\n');upper=text.upper()
   if upper.startswith('EHLO'):
    w.write(b'250-localhost\r\n250-SIZE 31457280\r\n250 8BITMIME\r\n');await w.drain()
   elif upper.startswith('HELO'):await reply(w,'250 localhost')
   elif upper.startswith('MAIL FROM:'):mail=True;rcpts=[];await reply(w,'250 OK')
   elif upper.startswith('RCPT TO:') and mail:rcpts.append(text[8:].strip());await reply(w,'250 OK')
   elif upper=='DATA' and mail and rcpts:
    await reply(w,'354 End data with <CR><LF>.<CR><LF>');buf=bytearray()
    while True:
     x=await r.readline()
     if not x:raise ConnectionError('client disconnected in DATA')
     if x in (b'.\r\n',b'.\n'):break
     if x.startswith(b'..'):x=x[1:]
     buf.extend(x)
     if len(buf)>MAX:
      await reply(w,'552 message too large');buf=None;break
    if buf is not None:
     try:await asyncio.to_thread(gmail_send_raw,bytes(buf));await reply(w,'250 accepted by Gmail API')
     except Exception:await reply(w,'451 OAuth Gmail send failed')
    mail=False;rcpts=[]
   elif upper=='RSET':mail=False;rcpts=[];await reply(w,'250 OK')
   elif upper=='NOOP':await reply(w,'250 OK')
   elif upper=='QUIT':await reply(w,'221 Bye');break
   else:await reply(w,'502 Command not implemented')
 finally:
  w.close();
  try:await w.wait_closed()
  except Exception:pass
async def main():
 server=await asyncio.start_server(handle,HOST,PORT)
 async with server:await server.serve_forever()
if __name__=='__main__':asyncio.run(main())
