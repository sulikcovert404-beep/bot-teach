import asyncio, io, os
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import select
from app.api.routes.admin_content import upload_content
from app.db.base import build_session_factory
from app.db.models import ContentVersion, SourceDocument

async def main():
    url=os.environ['DATABASE_URL']
    factory=build_session_factory(url)
    pdf=open('tests/fixtures/content_upload_test_book_fa.pdf','rb').read()
    docx=open('tests/fixtures/content_upload_test_book_fa.docx','rb').read()
    async with factory() as s:
        def f(data,name,mime):
            return UploadFile(file=io.BytesIO(data), filename=name, headers=Headers({'content-type':mime}))
        a=await upload_content(f(pdf,'../content_upload_test_book_fa.pdf','application/pdf'),'Staging Multipart فارسی','10','فیزیک','فصل اول','درس اول','staging-admin',s)
        b=await upload_content(f(docx,'content_upload_test_book_fa.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),'Staging Multipart فارسی DOCX','10','فیزیک','فصل اول','درس اول','staging-admin',s)
        c=await upload_content(f(pdf,'content_upload_test_book_fa.pdf','application/pdf'),'Staging Multipart فارسی','10','فیزیک','فصل اول','درس اول','staging-admin',s)
        print({'pdf':a,'docx':b,'duplicate_pdf':c})
        source=(await s.scalar(select(SourceDocument).where(SourceDocument.source_id==a['source_id']))); versions=(await s.execute(select(ContentVersion).where(ContentVersion.source_document_id==source.id))).scalars().all()
        print({'persistence_check':'completed','version_numbers':[v.version_number for v in versions],'all_draft':all(v.review_state=='DRAFT' for v in versions)})
    await factory.bind.dispose() if False else None
asyncio.run(main())

