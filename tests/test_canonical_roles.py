import pytest
from fastapi import HTTPException

from app.security.canonical import canonical_role


def test_canonical_role_accepts_target_roles():
    for role in ("SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"):
        assert canonical_role(role) == role

def test_canonical_role_rejects_legacy_or_missing_role():
    for role in ("ADMIN", None, "ROOT"):
        with pytest.raises(HTTPException) as exc:
            canonical_role(role)
        assert exc.value.status_code == 403
