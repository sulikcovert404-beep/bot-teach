from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.security.tokens import decode_access_token, decode_access_token_claims

bearer = HTTPBearer(auto_error=False)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        return decode_access_token(credentials.credentials, get_settings().jwt_secret)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def authorize_role(user_role: str, allowed_roles: set[str]) -> None:
    if user_role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def require_roles(*allowed_roles: str) -> Callable[..., str]:
    allowed = set(allowed_roles)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),  # noqa: B008
    ) -> str:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        try:
            claims = decode_access_token_claims(credentials.credentials, get_settings().jwt_secret)
            subject = claims.get("sub")
            role = claims.get("role")
            if not isinstance(subject, str) or not isinstance(role, str):
                raise TypeError("Token identity or role is missing")
            authorize_role(role, allowed)
            return subject
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return dependency
