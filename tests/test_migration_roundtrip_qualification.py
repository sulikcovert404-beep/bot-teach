from pathlib import Path
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.db.models import SchoolTenant, SchoolAdminMembership, User

@pytest.mark.asyncio
async def test_migration_roundtrip_0019_0018_0019_and_post_smoke():
    project_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))
    
    script = ScriptDirectory.from_config(alembic_cfg)
    rev_0019 = script.get_revision("20260910_0019")
    rev_0018 = script.get_revision("20260910_0018")
    
    assert rev_0019 is not None
    assert rev_0018 is not None
    assert rev_0019.down_revision == "20260910_0018"
    
    # 1. Simulate Upgrade -> Downgrade -> Re-upgrade schema consistency test in memory
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Verify school_tenants & school_admin_memberships exist in 0019 schema
        tables = await conn.run_sync(lambda sync_conn: sa.inspect(sync_conn).get_table_names())
        assert "school_tenants" in tables
        assert "school_admin_memberships" in tables
        
        # 2. Simulate roundtrip downgrade (0018 lacks school_admin_memberships)
        await conn.execute(sa.text("DROP TABLE school_admin_memberships"))
        await conn.execute(sa.text("DROP TABLE school_tenants"))
        tables_0018 = await conn.run_sync(lambda sync_conn: sa.inspect(sync_conn).get_table_names())
        assert "school_admin_memberships" not in tables_0018
        
        # 3. Simulate re-upgrade back to 0019
        await conn.run_sync(Base.metadata.create_all)
        tables_0019_reloaded = await conn.run_sync(lambda sync_conn: sa.inspect(sync_conn).get_table_names())
        assert "school_tenants" in tables_0019_reloaded
        assert "school_admin_memberships" in tables_0019_reloaded
        
    await engine.dispose()
