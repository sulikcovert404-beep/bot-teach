from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (
    ClassMembership,
    Classroom,
    ContentVersion,
    SchoolTenant,
    SourceDocument,
    StudentProfile,
    TeacherProfile,
    User,
)
from app.main import app
from app.security.tokens import create_access_token


@pytest.mark.asyncio
async def test_missing_tenant_context_fails_closed_for_authenticated_student(tmp_path: Path, monkeypatch):
    """An authenticated student without a resolved profile/tenant gets no content."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'missing-context.db'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add(User(id=990, username='orphan-student', role='STUDENT'))
        await s.commit()
    async def override():
        async with sessions() as s:
            yield s
    app.dependency_overrides[get_session] = override
    secret = 'x' * 32
    monkeypatch.setattr(get_settings(), 'jwt_secret', secret)
    token = create_access_token('990', secret, role='STUDENT')
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/v1/student/v2/classroom-content', headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200
        body = response.json()
        assert body['items'] == []
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()

@pytest.mark.asyncio
async def test_content_lifecycle_controls_student_retrieval(tmp_path: Path, monkeypatch):
    engine=create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'content.db'}")
    sessions=async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add_all([SchoolTenant(tenant_id='ct-a',school_name='A'),User(id=301,username='t',role='TEACHER'),User(id=302,username='s',role='STUDENT')]); await s.flush()
        tp=TeacherProfile(teacher_id=301,tenant_id='ct-a'); sp=StudentProfile(student_id=302); s.add_all([tp,sp]); await s.flush()
        cl=Classroom(classroom_key='ct-class',tenant_id='ct-a',teacher_profile_id=tp.id); s.add(cl); await s.flush(); s.add(ClassMembership(classroom_id=cl.id,student_id=sp.id))
        doc=SourceDocument(source_id='ct-src',title='محتوا',uri='memory://ct'); s.add(doc); await s.flush()
        v=ContentVersion(source_document_id=doc.id,owner_teacher_id=301,processing_state='PROCESSED',review_state='DRAFT',vector_sync_state='VECTOR_SYNCED',source_hash='a'*64); s.add(v); await s.commit(); vid, cid= v.id,cl.id
    async def override():
        async with sessions() as s: yield s
    app.dependency_overrides[get_session]=override
    secret='x'*32; monkeypatch.setattr(get_settings(),'jwt_secret',secret)
    th=create_access_token('301',secret,role='TEACHER'); st=create_access_token('302',secret,role='STUDENT')
    try:
      async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        base={'Authorization':f'Bearer {th}'}
        assert (await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {st}'})).json()['items']==[]
        assert (await client.post(f'/api/v1/teacher/v2/content/{vid}/review',headers=base,json={'action':'APPROVE'})).status_code==200
        pub=await client.post('/api/v1/teacher/v2/publications',headers=base,json={'content_version_id':vid,'classroom_id':cid}); assert pub.status_code==201
        got=await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {st}'}); assert len(got.json()['items'])==1
        assert (await client.post(f'/api/v1/teacher/v2/content/{vid}/review',headers=base,json={'action':'REVOKE'})).status_code==200
        gone=await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {st}'}); assert gone.json()['items']==[]
        # Rejected content cannot be published.
        async with sessions() as s2:
            rejected=ContentVersion(source_document_id=1,owner_teacher_id=301,version_number=2,processing_state='PROCESSED',review_state='DRAFT',vector_sync_state='VECTOR_SYNCED',source_hash='b'*64); s2.add(rejected); await s2.commit(); rid=rejected.id
        assert (await client.post(f'/api/v1/teacher/v2/content/{rid}/review',headers=base,json={'action':'REJECT'})).status_code==200
        assert (await client.post('/api/v1/teacher/v2/publications',headers=base,json={'content_version_id':rid,'classroom_id':cid})).status_code==409
        assert len((await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {st}'})).json()['items'])==0
    finally:
      app.dependency_overrides.pop(get_session,None); await engine.dispose()












@pytest.mark.asyncio
async def test_two_tenant_seed_ownership_is_deterministic():
    from sqlalchemy.pool import StaticPool
    engine=create_async_engine('sqlite+aiosqlite://',poolclass=StaticPool)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add_all([SchoolTenant(tenant_id='ra',school_name='A'),SchoolTenant(tenant_id='rb',school_name='B'),User(id=501,username='ra-teacher',role='TEACHER'),User(id=502,username='rb-teacher',role='TEACHER')]); await s.flush()
        ta=TeacherProfile(teacher_id=501,tenant_id='ra'); tb=TeacherProfile(teacher_id=502,tenant_id='rb'); s.add_all([ta,tb]); await s.flush()
        da=SourceDocument(source_id='ra-doc',title='A',uri='memory:a'); db=SourceDocument(source_id='rb-doc',title='B',uri='memory:b'); s.add_all([da,db]); await s.flush()
        va=ContentVersion(source_document_id=da.id,owner_teacher_id=501,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='a'*64); vb=ContentVersion(source_document_id=db.id,owner_teacher_id=502,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='b'*64); s.add_all([va,vb]); await s.commit()
        assert ta.tenant_id=='ra' and tb.tenant_id=='rb'; assert va.owner_teacher_id==501 and vb.owner_teacher_id==502; assert va.source_document_id != vb.source_document_id
    await engine.dispose()

@pytest.mark.asyncio
async def test_two_tenant_route_publish_denies_foreign_content(tmp_path: Path, monkeypatch):
    from sqlalchemy.pool import StaticPool
    engine=create_async_engine('sqlite+aiosqlite://',poolclass=StaticPool)
    sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add_all([SchoolTenant(tenant_id='x-a',school_name='A'),SchoolTenant(tenant_id='x-b',school_name='B'),User(id=601,username='xa',role='TEACHER'),User(id=602,username='xb',role='TEACHER')]); await s.flush()
        ta=TeacherProfile(teacher_id=601,tenant_id='x-a'); tb=TeacherProfile(teacher_id=602,tenant_id='x-b'); s.add_all([ta,tb]); await s.flush()
        ca=Classroom(classroom_key='xa-class',tenant_id='x-a',teacher_profile_id=ta.id); cb=Classroom(classroom_key='xb-class',tenant_id='x-b',teacher_profile_id=tb.id); s.add_all([ca,cb]); await s.flush()
        da=SourceDocument(source_id='xa-doc',title='A',uri='memory:a'); db=SourceDocument(source_id='xb-doc',title='B',uri='memory:b'); s.add_all([da,db]); await s.flush()
        va=ContentVersion(source_document_id=da.id,owner_teacher_id=601,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='a'*64); vb=ContentVersion(source_document_id=db.id,owner_teacher_id=602,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='b'*64); s.add_all([va,vb]); await s.commit(); bid,caid=vb.id,ca.id
    async def override():
        async with sessions() as s: yield s
    app.dependency_overrides[get_session]=override; secret='x'*32; monkeypatch.setattr(get_settings(),'jwt_secret',secret); tok=create_access_token('601',secret,role='TEACHER')
    try:
      async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        resp=await client.post('/api/v1/teacher/v2/publications',headers={'Authorization':f'Bearer {tok}'},json={'content_version_id':bid,'classroom_id':caid})
        assert resp.status_code==404, resp.text
    finally: app.dependency_overrides.pop(get_session,None); await engine.dispose()

@pytest.mark.asyncio
async def test_two_tenant_route_review_denies_foreign_content(tmp_path: Path, monkeypatch):
    from sqlalchemy.pool import StaticPool
    engine=create_async_engine('sqlite+aiosqlite://',poolclass=StaticPool); sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add_all([SchoolTenant(tenant_id='ra',school_name='A'),SchoolTenant(tenant_id='rb',school_name='B'),User(id=701,username='a',role='TEACHER'),User(id=702,username='b',role='TEACHER')]); await s.flush(); s.add_all([TeacherProfile(teacher_id=701,tenant_id='ra'),TeacherProfile(teacher_id=702,tenant_id='rb')]); await s.flush(); d=SourceDocument(source_id='rb-d',title='B',uri='memory:b'); s.add(d); await s.flush(); v=ContentVersion(source_document_id=d.id,owner_teacher_id=702,processing_state='PROCESSED',review_state='DRAFT',vector_sync_state='VECTOR_SYNCED',source_hash='b'*64); s.add(v); await s.commit(); vid=v.id
    async def override():
        async with sessions() as s: yield s
    app.dependency_overrides[get_session]=override; secret='x'*32; monkeypatch.setattr(get_settings(),'jwt_secret',secret); tok=create_access_token('701',secret,role='TEACHER')
    try:
      async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        resp=await client.post(f'/api/v1/teacher/v2/content/{vid}/review',headers={'Authorization':f'Bearer {tok}'},json={'action':'APPROVE'}); assert resp.status_code==404, resp.text
    finally: app.dependency_overrides.pop(get_session,None); await engine.dispose()

@pytest.mark.asyncio
async def test_two_tenant_review_and_student_retrieval_denials(tmp_path: Path, monkeypatch):
    from sqlalchemy.pool import StaticPool
    engine=create_async_engine('sqlite+aiosqlite://',poolclass=StaticPool); sessions=async_sessionmaker(engine,expire_on_commit=False)
    async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    async with sessions() as s:
        s.add_all([SchoolTenant(tenant_id='fa',school_name='A'),SchoolTenant(tenant_id='fb',school_name='B'),User(id=801,username='ta',role='TEACHER'),User(id=802,username='sa',role='STUDENT'),User(id=803,username='tb',role='TEACHER'),User(id=804,username='sb',role='STUDENT')]); await s.flush(); ta=TeacherProfile(teacher_id=801,tenant_id='fa'); tb=TeacherProfile(teacher_id=803,tenant_id='fb'); sa=StudentProfile(student_id=802); sb=StudentProfile(student_id=804); s.add_all([ta,tb,sa,sb]); await s.flush(); ca=Classroom(classroom_key='fa-c',tenant_id='fa',teacher_profile_id=ta.id); cb=Classroom(classroom_key='fb-c',tenant_id='fb',teacher_profile_id=tb.id); s.add_all([ca,cb]); await s.flush(); s.add_all([ClassMembership(classroom_id=ca.id,student_id=sa.id),ClassMembership(classroom_id=cb.id,student_id=sb.id)]); da=SourceDocument(source_id='fa-d',title='A',uri='a'); db=SourceDocument(source_id='fb-d',title='B',uri='b'); s.add_all([da,db]); await s.flush(); va=ContentVersion(source_document_id=da.id,owner_teacher_id=801,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='a'*64); vb=ContentVersion(source_document_id=db.id,owner_teacher_id=803,processing_state='PROCESSED',review_state='APPROVED',vector_sync_state='VECTOR_SYNCED',source_hash='b'*64); s.add_all([va,vb]); await s.commit(); aid,bid,caid,cbid=va.id,vb.id,ca.id,cb.id
    async def override():
        async with sessions() as s: yield s
    app.dependency_overrides[get_session]=override; secret='x'*32; monkeypatch.setattr(get_settings(),'jwt_secret',secret); ta_tok=create_access_token('801',secret,role='TEACHER'); sa_tok=create_access_token('802',secret,role='STUDENT'); sb_tok=create_access_token('804',secret,role='STUDENT')
    try:
      async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.post(f'/api/v1/teacher/v2/content/{bid}/review',headers={'Authorization':f'Bearer {ta_tok}'},json={'action':'APPROVE'})).status_code==404
        await client.post('/api/v1/teacher/v2/publications',headers={'Authorization':f'Bearer {ta_tok}'},json={'content_version_id':aid,'classroom_id':caid})
        # Tenant A student cannot see Tenant B publication; Tenant B student cannot see A content.
        assert [i['content_version_id'] for i in (await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {sa_tok}'})).json()['items']]==[aid]
        assert (await client.get('/api/v1/student/v2/classroom-content',headers={'Authorization':f'Bearer {sb_tok}'})).json()['items']==[]
    finally: app.dependency_overrides.pop(get_session,None); await engine.dispose()

