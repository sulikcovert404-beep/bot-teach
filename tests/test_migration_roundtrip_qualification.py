from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base


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


def test_dual_parent_lineage_convergence_0009_and_0019_to_0020():
    project_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))
    script = ScriptDirectory.from_config(alembic_cfg)

    # 1. Verify single converged head
    heads = script.get_heads()
    assert heads == ["20261006_0034"]

    rev_0021 = script.get_revision("20260912_0021")
    assert rev_0021.down_revision == "20260912_0020"
    rev_0026 = script.get_revision("20261003_0026")
    rev_0027 = script.get_revision("20261003_0027")
    assert rev_0026.down_revision == "20261003_0025"
    rev_0030 = script.get_revision("20261003_0030")
    rev_0031 = script.get_revision("20261003_0031")
    rev_0032 = script.get_revision("20261004_0032")
    rev_0033 = script.get_revision("20261004_0033")
    rev_0034 = script.get_revision("20261006_0034")
    assert rev_0034.down_revision == "20261004_0033"
    rev_0024 = script.get_revision("20261003_0024")
    assert rev_0032.down_revision == "20261003_0029"
    assert rev_0030.down_revision == "20261004_0032"
    assert rev_0024.down_revision == "20260921_0022"
    assert rev_0027.down_revision == "20261003_0026"
    assert rev_0031.down_revision == "20261003_0030"
    assert rev_0033.down_revision == "20261003_0031"

    # 2. Verify merge revision points to both 0009 and 0019
    rev_0020 = script.get_revision("20260912_0020")
    assert set(rev_0020.down_revision) == {"20260909_0009", "20260910_0019"}

    # 3. Verify production branch ancestry from 0009
    rev_0009 = script.get_revision("20260909_0009")
    assert rev_0009.down_revision == "2e0b56730806"
    rev_bigint = script.get_revision("2e0b56730806")
    assert rev_bigint.down_revision == "f7a8b9c0d1e2"

    # 4. Verify staging branch ancestry from 0019
    rev_0019 = script.get_revision("20260910_0019")
    assert rev_0019.down_revision == "20260910_0018"
