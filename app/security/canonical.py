from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.security.dependencies import bearer
from app.security.tokens import decode_access_token_claims

CANONICAL_ROLES = frozenset({"SUPER_ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT"})


def canonical_role(role: object) -> str:
    if not isinstance(role, str) or role not in CANONICAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Canonical role required")
    return role


def require_canonical_roles(*allowed_roles: str) -> Callable[..., str]:
    allowed = set(allowed_roles)
    if not allowed or not allowed <= CANONICAL_ROLES:
        raise ValueError("Allowed roles must be canonical")

    def dependency(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        try:
            claims = decode_access_token_claims(credentials.credentials, get_settings().jwt_secret)
            subject = claims.get("sub")
            role = canonical_role(claims.get("role"))
            if not isinstance(subject, str) or role not in allowed:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
            return subject
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return dependency

