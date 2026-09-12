from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.security.canonical import CANONICAL_ROLES, canonical_role
from app.security.dependencies import bearer
from app.security.tokens import decode_access_token_claims


@dataclass(frozen=True)
class CanonicalPrincipal:
    subject: str
    role: str

def require_principal(*allowed_roles: str) -> Callable[..., CanonicalPrincipal]:
    allowed=set(allowed_roles)
    if not allowed <= CANONICAL_ROLES: raise ValueError('Allowed roles must be canonical')
    def dependency(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> CanonicalPrincipal:
        if credentials is None: raise HTTPException(status_code=401, detail='Authentication required')
        try:
            claims=decode_access_token_claims(credentials.credentials,get_settings().jwt_secret)
            subject=claims.get('sub'); role=canonical_role(claims.get('role'))
            if not isinstance(subject,str) or role not in allowed: raise HTTPException(status_code=403,detail='Insufficient role')
            return CanonicalPrincipal(subject,role)
        except HTTPException: raise
        except Exception as exc: raise HTTPException(status_code=401,detail='Invalid token') from exc
    return dependency

