"""Exercise fail-closed contract, synthetic correction, idempotent resume, and recheck."""
from __future__ import annotations

import asyncio
import os
import runpy
import sys
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")

PORT=int(os.environ['GATE738E_LOCAL_PG_PORT'])
assert os.environ.get('GATE738F_DISPOSABLE')=='1'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ns=runpy.run_path(os.path.join(ROOT,'tests','gate738f_qualification.py'))
async def main():
 db='gate738e_'+uuid4().hex
 await ns['prepare'](db,3,0)
 c=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database=db)
 row=await c.fetchrow("select s.id,s.student_id from student_submissions s order by s.id limit 1")
 teacher=await c.fetchval("select id from users where role='TEACHER' order by id limit 1")
 await c.execute("update student_submissions set status='NOT_SUBMITTED',content_json=NULL,submitted_at=NULL where id=$1",row['id'])
 await c.execute("insert into submission_reviews(submission_id,tenant_id,review_status,reviewed_by) values($1,'gate738f','REVIEWED',$2)",row['id'],teacher)
 await c.close()
 for rev in ('20261003_0027','20261003_0028','20261003_0029'): ns['alembic'](db,rev)
 output=None
 try:
  _,output,_=ns['backfill'](db,limit=None,batch=100)
 except RuntimeError as e:
  output=str(e)
 assert 'DO NOT CONTRACT' in output
 c=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database=db)
 failed=await c.fetchrow('select status,processed_submissions from submission_revision_backfill_state')
 version=await c.fetchval('select version_num from alembic_version')
 await c.execute('delete from submission_reviews where submission_id=$1',row['id'])
 await c.close()
 env=os.environ.copy(); env['DATABASE_URL']=f'postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}'
 refusal=await asyncio.create_subprocess_exec(sys.executable,'-B','-m','alembic','upgrade','20261003_0030',cwd=ROOT,env=env,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
 _,refusal_stderr=await asyncio.wait_for(refusal.communicate(),timeout=60)
 assert refusal.returncode!=0 and 'must be validated' in refusal_stderr.decode(errors='replace')
 _,_out1,rc1=ns['backfill'](db,limit=None,batch=100); assert rc1==0
 _,_out2,rc2=ns['backfill'](db,limit=None,batch=100); assert rc2==0
 ns['alembic'](db,'20261003_0030'); ns['alembic'](db,'20261003_0031')
 c=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database=db)
 final=await c.fetchrow("select version_num from alembic_version")
 integrity=await c.fetchrow("select (select count(*) from student_submissions where status in ('SUBMITTED','REVIEWED') and current_revision_id is null) missing_pointer,(select count(*) from submission_reviews where submission_revision_id is null) unlinked_reviews,(select count(*) from submission_revisions) revisions")
 await c.close()
 assert final['version_num']=='20261003_0031' and integrity['missing_pointer']==0 and integrity['unlinked_reviews']==0
 print({'database':db,'invalid_review_preflight':'BLOCKED_AS_EXPECTED','failed_state':dict(failed),'revision_after_failure':version,'contract_refusal':'PASS_FAIL_CLOSED','synthetic_data_correction':'removed_invalid_test_review_only','backfill_resume':'PASS','validated_replay':'PASS','final_revision':final['version_num'],'final_integrity':dict(integrity)})
if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")
