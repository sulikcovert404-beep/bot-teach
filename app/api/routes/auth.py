from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.telegram import validate_web_app_init_data
from app.core.config import get_settings
from app.db.base import build_session_factory
from app.db.models import User
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=10_000)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(status_code=503, detail="Database unavailable")
    factory = build_session_factory(settings.database_url)
    async with factory() as session:
        yield session


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    request: TelegramAuthRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> AuthResponse:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.jwt_secret:
        raise HTTPException(status_code=503, detail="Authentication unavailable")
    try:
        identity = validate_web_app_init_data(request.init_data, settings.telegram_bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid init data") from exc
    user = await session.scalar(select(User).where(User.telegram_user_id == identity.telegram_user_id))
    if user is None:
        user = User(telegram_user_id=identity.telegram_user_id, username=identity.username)
        session.add(user)
    else:
        user.username = identity.username
    await session.commit()
    await session.refresh(user)
    token = create_access_token(str(user.id), settings.jwt_secret, role=user.role)
    return AuthResponse(access_token=token, user_id=user.id, role=user.role)
