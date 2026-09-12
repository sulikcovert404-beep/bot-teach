import pytest

from app.db.base import InvalidTenantContext, set_tenant_context


@pytest.mark.asyncio
async def test_tenant_context_requires_transaction():
    class FakeSession:
        def in_transaction(self): return False
    with pytest.raises(InvalidTenantContext):
        await set_tenant_context(FakeSession(), "00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_tenant_context_rejects_invalid_opaque_identifier():
    class FakeSession:
        def in_transaction(self): return True
    with pytest.raises(InvalidTenantContext):
        await set_tenant_context(FakeSession(), "tenant a")


@pytest.mark.asyncio
async def test_tenant_context_binds_parameter_and_local_flag():
    calls = []
    class FakeSession:
        def in_transaction(self): return True
        async def execute(self, statement, params): calls.append((str(statement), params))
    value = await set_tenant_context(FakeSession(), "tenant-a")
    assert value == "tenant-a"
    assert "set_config('app.tenant_id'" in calls[0][0]
    assert calls[0][1] == {"tenant_id": value}


@pytest.mark.asyncio
async def test_tenant_context_rejects_empty_and_oversized_values():
    class FakeSession:
        def in_transaction(self): return True
    with pytest.raises(InvalidTenantContext):
        await set_tenant_context(FakeSession(), "")
    with pytest.raises(InvalidTenantContext):
        await set_tenant_context(FakeSession(), "a" * 65)


@pytest.mark.asyncio
async def test_tenant_context_preserves_canonical_opaque_value():
    calls = []
    class FakeSession:
        def in_transaction(self): return True
        async def execute(self, statement, params): calls.append(params)
    value = await set_tenant_context(FakeSession(), "Sch-Helli-01")
    assert value == "Sch-Helli-01"
    assert calls == [{"tenant_id": "Sch-Helli-01"}]


@pytest.mark.asyncio
async def test_tenant_context_rejects_non_string_values():
    class FakeSession:
        def in_transaction(self): return True
    with pytest.raises(InvalidTenantContext):
        await set_tenant_context(FakeSession(), 123)  # type: ignore[arg-type]
