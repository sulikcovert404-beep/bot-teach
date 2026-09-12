import asyncio,io,os
from fastapi import UploadFile,HTTPException
from starlette.datastructures import Headers
import app.api.routes.admin_content as m
from app.db.base import build_session_factory
from sqlalchemy import select
from app.db.models import SourceDocument,ContentVersion
async def main():
 fct=build_session_factory(os.environ['DATABASE_URL']); pdf=open('/app/tests/fixtures/content_upload_test_book_fa.pdf','rb').read()
 async with fct() as s:
  def f(d,n,mime): return UploadFile(file=io.BytesIO(d),filename=n,headers=Headers({'content-type':mime}))
  out={}
  for k,d,n,mi in [('invalid_mime',pdf,'x.pdf','text/plain'),('oversized',b'x'*(25*1024*1024+1),'x.pdf','application/pdf'),('malformed',b'%PDF-1.0','x.pdf','application/pdf')]:
   try: await m.upload_content(f(d,n,mi),'neg','10','x','c','l','a',s); out[k]='unexpected_success'
   except HTTPException as e: out[k]=e.status_code
  orig=m._extract_pdf; m._extract_pdf=lambda d:''
  try: out['empty_extraction']=(await m.upload_content(f(pdf,'empty.pdf','application/pdf'),'empty','10','x','c','l','a',s))['processing_state']
  finally: m._extract_pdf=orig
  first=await m.upload_content(f(pdf,'dup.pdf','application/pdf'),'final-dup','10','x','c','l','a',s)
  second=await m.upload_content(f(pdf,'dup.pdf','application/pdf'),'final-dup','10','x','c','l','a',s)
  src=await s.scalar(select(SourceDocument).where(SourceDocument.source_id==first['source_id']))
  vs=(await s.execute(select(ContentVersion).where(ContentVersion.source_document_id==src.id))).scalars().all()
  out['duplicate_versions']=[v.version_number for v in vs]; out['no_overwrite']=second['content_version_id']!=first['content_version_id']
  print(out)
asyncio.run(main())
