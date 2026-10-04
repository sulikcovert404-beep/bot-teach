import pytest
from fastapi.openapi.utils import get_openapi
from httpx import ASGITransport, AsyncClient

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.main import app
from app.security.tokens import create_access_token


@pytest.mark.asyncio
async def test_legacy_membership_route_keeps_auth_and_returns_410_without_db(monkeypatch):
    secret = "gate738t-test-secret-32-bytes-long"
    monkeypatch.setattr(get_settings(), "jwt_secret", secret)
    session_dependency_calls = 0

    async def unexpected_session_dependency():
        nonlocal session_dependency_calls
        session_dependency_calls += 1
        raise AssertionError("retired legacy membership route resolved a DB session")

    previous_override = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = unexpected_session_dependency
    teacher_token = create_access_token("teacher-1", secret, role="TEACHER")
    admin_token = create_access_token("admin-1", secret, role="ADMIN")
    student_token = create_access_token("student-1", secret, role="STUDENT")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            valid_request = {
                "url": "/api/v1/teacher/v2/classrooms/123/members",
                "json": {"student_id": 456},
            }
            unauthenticated = await client.post(**valid_request)
            forbidden = await client.post(
                **valid_request,
                headers={"Authorization": f"Bearer {student_token}"},
            )
            admin_response = await client.post(
                **valid_request,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            authenticated = await client.post(
                **valid_request,
                headers={"Authorization": f"Bearer {teacher_token}"},
            )
            malformed = await client.post(
                "/api/v1/teacher/v2/classrooms/123/members",
                headers={"Authorization": f"Bearer {teacher_token}"},
                json={},
            )

        assert unauthenticated.status_code == 401
        assert forbidden.status_code == 403
        assert admin_response.status_code == 410
        assert authenticated.status_code == 410
        assert authenticated.json() == {
            "detail": "Legacy classroom membership mutation is disabled"
        }
        assert malformed.status_code == 422
        assert session_dependency_calls == 0
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous_override


def test_legacy_membership_openapi_matches_retired_runtime_contract():
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        routes=app.routes,
    )
    operation = schema["paths"][
        "/api/v1/teacher/v2/classrooms/{classroom_id}/members"
    ]["post"]

    assert operation["operationId"] == (
        "add_persistent_member_api_v1_teacher_v2_classrooms__classroom_id__members_post"
    )
    assert operation["deprecated"] is True
    assert "Retired endpoint" in operation["description"]
    assert "201" not in operation["responses"]
    assert operation["responses"]["410"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/LegacyMembershipRetiredResponse"
    }
    assert operation["responses"]["422"]["description"] == "Validation Error"
    assert schema["components"]["schemas"]["LegacyMembershipRetiredResponse"] == {
        "properties": {"detail": {"type": "string", "title": "Detail"}},
        "type": "object",
        "required": ["detail"],
        "title": "LegacyMembershipRetiredResponse",
    }
