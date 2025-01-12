from fastapi import APIRouter

from backend.routers.api.agency import agency_router
from backend.routers.api.agent import agent_router
from backend.routers.api.message import message_router
from backend.routers.api.profile import profile_router
from backend.routers.api.session import session_router
from backend.routers.api.skill import skill_router
from backend.routers.api.user import user_router
from backend.routers.api.version import version_router

api_router = APIRouter(
    responses={404: {"description": "Not found"}},
)

api_router.include_router(skill_router)
api_router.include_router(agent_router)
api_router.include_router(agency_router)
api_router.include_router(session_router)
api_router.include_router(message_router)
api_router.include_router(version_router)
api_router.include_router(user_router)
api_router.include_router(profile_router)
