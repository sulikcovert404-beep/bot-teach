"""Measure the final contract migration lock against synthetic PostgreSQL rows."""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")

PORT=int(os.environ['GATE738E_LOCAL_PG_PORT'])
assert os.environ.get('GATE738F_DISPOSABLE')=='1'
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def alembic(db, rev):
    env=os.environ.copy(); env['DATABASE_URL']=f'postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}'
    p=subprocess.run([sys.executable,'-B','-m','alembic','upgrade',rev],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180,check=False)
    if p.returncode: raise RuntimeError(p.stderr[-2500:])
    return p

async def main():
    ns=__import__('runpy').run_path(os.path.join(ROOT,'tests','gate738f_qualification.py'))
    db='gate738e_'+uuid4().hex
    await ns['prepare'](db,5000,250)
    for rev in ('20261003_0027','20261003_0028','20261003_0029'): alembic(db,rev)
    elapsed, output, code=ns['backfill'](db,limit=None,batch=500)
    if code: raise RuntimeError(output[-2500:])

    reader=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database=db)
    tx=reader.transaction(); await tx.start()
    await reader.fetchval('SELECT count(*) FROM student_submissions')
    env=os.environ.copy(); env['DATABASE_URL']=f'postgresql+asyncpg://gate738e@127.0.0.1:{PORT}/{db}'
    start=time.perf_counter()
    proc=await asyncio.create_subprocess_exec(
        sys.executable,'-B','-m','alembic','upgrade','20261003_0030',cwd=ROOT,env=env,
        stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    admin=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database='gate738e_test')
    waiter=None
    for _ in range(300):
        await asyncio.sleep(.05)
        waiter=await admin.fetchrow("""SELECT pid,wait_event_type,wait_event,left(query,300) query
            FROM pg_stat_activity WHERE datname=$1 AND wait_event_type='Lock' ORDER BY query_start LIMIT 1""",db)
        if waiter: break
        if proc.returncode is not None: break
    wait_ms=None; lock_rows=[]; writer_result='not_attempted'
    if waiter:
        wait_ms=round((time.perf_counter()-start)*1000,1)
        lock_rows=await admin.fetch("""SELECT mode,granted,coalesce(relation::regclass::text,'') relation
          FROM pg_locks WHERE pid=$1 ORDER BY granted,mode""",waiter['pid'])
        writer=await asyncpg.connect(host='127.0.0.1',port=PORT,user='gate738e',database=db,command_timeout=1)
        try:
            await writer.execute("UPDATE student_submissions SET updated_at=now() WHERE id=(SELECT min(id) FROM student_submissions)")
            writer_result='completed_while_contract_waited'
        except (TimeoutError,asyncpg.QueryCanceledError) as e:
            writer_result=f'blocked_timeout_sqlstate={getattr(e,"sqlstate",None)}'
        finally: await writer.close()
    await tx.commit(); await reader.close()
    _,stderr_bytes=await asyncio.wait_for(proc.communicate(),timeout=60)
    stderr=stderr_bytes.decode(errors='replace')
    total_ms=round((time.perf_counter()-start)*1000,1)
    await admin.close()
    if proc.returncode: raise RuntimeError(stderr[-2500:])
    print({'database':db,'rows':5000,'backfill_seconds':round(elapsed,3),'contract_wait_observed':bool(waiter),
      'wait_ms_at_observation':wait_ms,'wait_event':dict(waiter) if waiter else None,
      'lock_rows': [dict(r) for r in lock_rows],'writer_while_waiting':writer_result,
      'total_contract_elapsed_ms_includes_hold':total_ms,'released_reader':'yes','contract_result':'PASS'})

if __name__ == "__main__":
    raise SystemExit("Retired Gate738F pre-control-plane harness; use the explicit Gate738P staged flow.")
