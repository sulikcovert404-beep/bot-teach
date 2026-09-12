import asyncio, io, os
from fastapi import UploadFile, HTTPException
from starlette.datastructures import Headers
from app.api.routes.admin_content import upload_content
from app.db.base import build_session_factory

async def main():
 fct=build_session_factory(os.environ['DATABASE_URL'])
 async with fct() as s:
  def f(data,name,mime): return UploadFile(file=io.BytesIO(data),filename=name,headers=Headers({'content-type':mime}))
  cases=[('invalid_mime',b'abc','x.txt','text/plain'),('oversize',b'x'*(25*1024*1024+1),'x.pdf','application/pdf'),('empty_pdf',b'%PDF-1.0','empty.pdf','application/pdf')]
  out={}
  for n,d,fn,m in cases:
   try: await upload_content(f(d,fn,m),'Negative staging','10','فیزیک','فصل','درس','staging-admin',s); out[n]='unexpected_success'
   except HTTPException as e: out[n]=e.status_code
  print(out)
asyncio.run(main())
