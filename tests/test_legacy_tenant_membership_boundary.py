import asyncio

import pytest
from fastapi import HTTPException

from app.api.routes.teacher import PersistentStudentRequest, add_persistent_member


def test_legacy_class_membership_endpoint_fails_closed_without_database_write():
    async def invoke():
        with pytest.raises(HTTPException) as exc_info:
            await add_persistent_member(
                classroom_id=123,
                req=PersistentStudentRequest(student_id=456),
                subject="789",
            )
        assert exc_info.value.status_code == 410
        assert exc_info.value.detail == "Legacy classroom membership mutation is disabled"

    asyncio.run(invoke())
