"""Read-only app_runtime ACL/RLS inventory on a Gate-owned disposable DB.

The disposable cluster must be loopback-only. This runner creates and drops one
uniquely named database, installs the frozen candidate, and prints catalog
metadata without emitting a DSN or credential.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import asyncpg

if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_DSN = os.environ["GATE738H_ADMIN_DSN"]
assert os.environ.get("GATE738H_DISPOSABLE") == "1"
parsed = urlparse(ADMIN_DSN)
assert parsed.scheme in {"postgres", "postgresql"}
assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
assert parsed.path.lstrip("/") == "postgres"


def dsn(database: str, sqlalchemy: bool = False) -> str:
    value = urlunparse(parsed._replace(path=f"/{database}"))
    return value.replace("postgresql://", "postgresql+asyncpg://", 1) if sqlalchemy else value


async def main() -> None:
    admin = await asyncpg.connect(ADMIN_DSN)
    database = "gate738h_acl_" + uuid4().hex
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname='app_runtime'"):
            await admin.execute("CREATE ROLE app_runtime LOGIN NOSUPERUSER NOBYPASSRLS")
        await admin.execute(f'CREATE DATABASE "{database}"')
    finally:
        await admin.close()

    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = dsn(database, sqlalchemy=True)
        run = await asyncio.create_subprocess_exec(
            sys.executable, "-B", "-m", "alembic", "upgrade", "20261003_0031",
            cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await asyncio.wait_for(run.communicate(), timeout=240)
        if run.returncode:
            raise RuntimeError(stderr.decode(errors="replace")[-3000:])
        connection = await asyncpg.connect(dsn(database))
        try:
            role = await connection.fetchrow(
                "SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication "
                "FROM pg_roles WHERE rolname='app_runtime'"
            )
            schema = await connection.fetchrow("""
                SELECT has_schema_privilege('app_runtime','public','USAGE') AS usage,
                       has_schema_privilege('app_runtime','public','CREATE') AS create
            """)
            relations = await connection.fetch("""
                SELECT n.nspname AS schema_name,c.relname AS relation_name,c.relkind,
                       has_table_privilege('app_runtime',c.oid,'SELECT') AS select,
                       has_table_privilege('app_runtime',c.oid,'INSERT') AS insert,
                       has_table_privilege('app_runtime',c.oid,'UPDATE') AS update,
                       has_table_privilege('app_runtime',c.oid,'DELETE') AS delete,
                       has_table_privilege('app_runtime',c.oid,'TRUNCATE') AS truncate,
                       has_table_privilege('app_runtime',c.oid,'REFERENCES') AS references,
                       has_table_privilege('app_runtime',c.oid,'TRIGGER') AS trigger,
                       c.relrowsecurity AS rls_enabled,c.relforcerowsecurity AS rls_forced
                  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                 WHERE n.nspname='public' AND c.relkind IN ('r','p','S','v','m','f')
                   AND c.relname IN ('student_submissions','submission_reviews',
                                     'submission_revisions','submission_revision_backfill_state',
                                     'submission_revision_rollout_state','student_submissions_id_seq',
                                     'submission_reviews_id_seq','submission_revisions_id_seq')
                 ORDER BY c.relkind,c.relname
            """)
            columns = await connection.fetch("""
                SELECT c.relname AS relation_name,a.attname AS column_name,
                       has_column_privilege('app_runtime',c.oid,a.attnum,'SELECT') AS select,
                       has_column_privilege('app_runtime',c.oid,a.attnum,'INSERT') AS insert,
                       has_column_privilege('app_runtime',c.oid,a.attnum,'UPDATE') AS update,
                       has_column_privilege('app_runtime',c.oid,a.attnum,'REFERENCES') AS references
                  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                  JOIN pg_attribute a ON a.attrelid=c.oid
                 WHERE n.nspname='public' AND c.relkind IN ('r','p')
                   AND c.relname IN ('student_submissions','submission_reviews','submission_revisions')
                   AND a.attnum>0 AND NOT a.attisdropped
                   AND (has_column_privilege('app_runtime',c.oid,a.attnum,'SELECT')
                     OR has_column_privilege('app_runtime',c.oid,a.attnum,'INSERT')
                     OR has_column_privilege('app_runtime',c.oid,a.attnum,'UPDATE')
                     OR has_column_privilege('app_runtime',c.oid,a.attnum,'REFERENCES'))
                 ORDER BY c.relname,a.attnum
             """)
            sequences = await connection.fetch("""
                SELECT c.relname AS sequence_name,
                       has_sequence_privilege('app_runtime',c.oid,'USAGE') AS usage,
                       has_sequence_privilege('app_runtime',c.oid,'SELECT') AS select,
                       has_sequence_privilege('app_runtime',c.oid,'UPDATE') AS update
                  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                 WHERE n.nspname='public' AND c.relkind='S'
                   AND c.relname IN ('student_submissions_id_seq','submission_reviews_id_seq',
                                     'submission_revisions_id_seq')
                 ORDER BY c.relname
            """)
            functions = await connection.fetch("""
                SELECT p.oid::regprocedure::text AS signature,owner.rolname AS owner,
                       p.prosecdef AS security_definer,p.proconfig AS settings,
                       has_function_privilege('app_runtime',p.oid,'EXECUTE') AS runtime_execute,
                       has_function_privilege('public',p.oid,'EXECUTE') AS public_execute
                  FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                  JOIN pg_roles owner ON owner.oid=p.proowner
                 WHERE n.nspname='public' AND p.prosecdef
                   AND (p.proname LIKE 'gate738e_%' OR p.proname IN
                       ('bootstrap_school_tenant','provision_tenant_membership',
                        'revoke_tenant_membership','get_tenant_membership'))
                 ORDER BY 1
            """)
            policies = await connection.fetch("""
                SELECT schemaname,tablename,policyname,permissive,roles,cmd,qual,with_check
                   FROM pg_policies WHERE schemaname='public' AND tablename IN
                       ('student_submissions','submission_reviews','submission_revisions')
                  ORDER BY tablename,policyname
            """)
            memberships = await connection.fetch("""
                SELECT granted.rolname AS granted_role, m.admin_option,
                       m.inherit_option, m.set_option
                  FROM pg_auth_members m
                  JOIN pg_roles granted ON granted.oid=m.roleid
                  JOIN pg_roles member ON member.oid=m.member
                 WHERE member.rolname='app_runtime'
                 ORDER BY granted.rolname
            """)
            default_acls = await connection.fetch("""
                SELECT owner.rolname AS owner_role, n.nspname AS schema_name,
                       d.defaclobjtype AS object_type, d.defaclacl::text AS acl
                  FROM pg_default_acl d
                  JOIN pg_roles owner ON owner.oid=d.defaclrole
                  LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
                 ORDER BY owner_role,schema_name,object_type
            """)
            public_privileges = await connection.fetch("""
                SELECT n.nspname AS schema_name, c.relname AS relation_name,
                       c.relkind,
                       has_table_privilege('public',c.oid,'SELECT') AS public_select,
                       has_table_privilege('public',c.oid,'INSERT') AS public_insert,
                       has_table_privilege('public',c.oid,'UPDATE') AS public_update,
                       has_table_privilege('public',c.oid,'DELETE') AS public_delete,
                       has_table_privilege('public',c.oid,'TRUNCATE') AS public_truncate,
                       has_table_privilege('public',c.oid,'REFERENCES') AS public_references,
                       has_table_privilege('public',c.oid,'TRIGGER') AS public_trigger
                  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                 WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f')
                 ORDER BY c.relname
            """)
            assert not role["rolsuper"] and not role["rolbypassrls"]
            assert not schema["create"]
            assert not memberships, memberships
            assert not default_acls, default_acls
            unsafe_public = [row for row in public_privileges if any(row[key] for key in (
                "public_insert", "public_update", "public_delete", "public_truncate",
                "public_references", "public_trigger",
            ))]
            assert not unsafe_public, unsafe_public
            by_name = {row["relation_name"]: row for row in relations}
            for relation in ("student_submissions", "submission_reviews"):
                assert not any(by_name[relation][grant] for grant in
                               ("insert", "update", "delete", "truncate", "references", "trigger"))
            assert by_name["submission_revisions"]["select"]
            assert by_name["submission_revisions"]["insert"]
            assert not any(by_name["submission_revisions"][grant] for grant in
                           ("update", "delete", "truncate", "references", "trigger"))
            sequence_map = {row["sequence_name"]: row for row in sequences}
            assert set(sequence_map) == {
                "student_submissions_id_seq", "submission_reviews_id_seq",
                "submission_revisions_id_seq",
            }
            assert all(row["usage"] and not row["select"] and not row["update"]
                       for row in sequence_map.values())
            column_map = {}
            for row in columns:
                column_map.setdefault(row["relation_name"], {"insert": set(), "update": set()})
                if row["insert"]:
                    column_map[row["relation_name"]]["insert"].add(row["column_name"])
                if row["update"]:
                    column_map[row["relation_name"]]["update"].add(row["column_name"])
            assert column_map["student_submissions"]["insert"] == {
                "assignment_id", "student_id", "tenant_id", "status", "revision"}
            assert column_map["student_submissions"]["update"] == {
                "current_revision_id", "revision", "content_json", "submitted_at", "status"}
            assert column_map["submission_reviews"]["insert"] == {
                "submission_id", "submission_revision_id", "tenant_id", "association_provenance",
                "review_status", "score", "teacher_feedback", "reviewed_by", "reviewed_at"}
            assert column_map["submission_reviews"]["update"] == {
                "association_provenance", "review_status", "score", "teacher_feedback",
                "reviewed_by", "reviewed_at"}
            bridge = {row["signature"].split("(")[0]: row for row in functions
                      if row["signature"].startswith("gate738e_")}
            assert set(bridge) == {
                "gate738e_sync_legacy_submission_revision",
                "gate738e_sync_legacy_submission_review",
            }
            for function in bridge.values():
                assert function["owner"] == "postgres"
                assert function["security_definer"]
                assert function["settings"] == ["search_path=pg_catalog"]
                assert not function["public_execute"]
                assert not function["runtime_execute"]
            rls = {row["tablename"]: row for row in policies}
            assert all(table in rls for table in
                       ("student_submissions", "submission_reviews", "submission_revisions"))
            assert by_name["submission_revisions"]["rls_enabled"]
            assert by_name["submission_revisions"]["rls_forced"]
            print(json.dumps({
                "role": dict(role), "public_schema": dict(schema),
                "relations": [dict(row) for row in relations],
                "column_grants": [dict(row) for row in columns],
                "sequences": [dict(row) for row in sequences],
                "functions": [dict(row) for row in functions],
                "rls_policies": [dict(row) for row in policies],
                "role_memberships": [dict(row) for row in memberships],
                "default_acl_entries": [dict(row) for row in default_acls],
                "public_relations_checked": len(public_privileges),
                "public_relations_with_write_or_ddl_grants": [dict(row) for row in unsafe_public],
                "verdict": "INVENTORY_CAPTURED",
            }, default=str, indent=2))
        finally:
            await connection.close()
    finally:
        admin = await asyncpg.connect(ADMIN_DSN)
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        finally:
            await admin.close()


if __name__ == "__main__":
    raise SystemExit("Retired Gate738H pre-control-plane harness; use the explicit Gate738P staged flow.")
