from fastapi import APIRouter

from app.domain.identity.schemas import PlatformInfo

router = APIRouter()


@router.get("/platform", response_model=PlatformInfo, tags=["platform"])
async def platform_info() -> PlatformInfo:
    return PlatformInfo(name="AI Education Platform Iran", api_version="v1")

