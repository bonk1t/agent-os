from fastapi import APIRouter

from backend.models.response_models import VersionResponse
from backend.version import VERSION

version_router = APIRouter(
    tags=["version"],
)


@version_router.get("/version")
async def get_version() -> VersionResponse:
    return VersionResponse(data={"version": VERSION})
