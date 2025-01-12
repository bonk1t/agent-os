from fastapi import Depends, HTTPException, WebSocket
from redis import asyncio as aioredis

from backend.repositories.agency_config_storage import AgencyConfigStorage
from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.session_storage import SessionConfigStorage
from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.repositories.user_profile_storage import UserProfileStorage
from backend.repositories.user_variable_storage import UserVariableStorage
from backend.services.adapters.agency_adapter import AgencyAdapter
from backend.services.adapters.agent_adapter import AgentAdapter
from backend.services.adapters.session_adapter import SessionAdapter
from backend.services.agency_manager import AgencyManager
from backend.services.agent_manager import AgentManager
from backend.services.auth_service import AuthService
from backend.services.message_manager import MessageManager
from backend.services.redis_cache_manager import RedisCacheManager
from backend.services.session_manager import SessionManager
from backend.services.skill_manager import SkillManager
from backend.services.user_profile_manager import UserProfileManager
from backend.services.user_variable_manager import UserVariableManager
from backend.services.websocket.websocket_connection_manager import WebSocketConnectionManager
from backend.services.websocket.websocket_handler import WebSocketHandler
from backend.settings import settings


async def get_websocket(websocket: WebSocket):
    # Make sure the connection is secure for non-localhost connections
    if websocket.url.scheme != "wss" and websocket.url.hostname not in ["localhost", "127.0.0.1", "testserver"]:
        await websocket.close(code=1000)  # Normal closure
        raise HTTPException(status_code=400, detail="Insecure WebSocket connection not allowed.")
    return websocket


def get_redis() -> aioredis.Redis:
    redis_url = str(settings.redis_tls_url or settings.redis_url)
    redis = aioredis.from_url(redis_url, decode_responses=False)
    return redis


def get_agent_adapter(
    skill_config_storage: SkillConfigStorage = Depends(SkillConfigStorage),
) -> AgentAdapter:
    return AgentAdapter(skill_config_storage)


def get_agency_adapter(
    agent_flow_spec_storage: AgentFlowSpecStorage = Depends(AgentFlowSpecStorage),
    agent_adapter: AgentAdapter = Depends(get_agent_adapter),
) -> AgencyAdapter:
    return AgencyAdapter(agent_flow_spec_storage, agent_adapter)


def get_session_adapter(
    agency_config_storage: AgencyConfigStorage = Depends(AgencyConfigStorage),
    agency_adapter: AgencyAdapter = Depends(get_agency_adapter),
) -> SessionAdapter:
    return SessionAdapter(agency_config_storage, agency_adapter)


def get_redis_cache_manager(redis: aioredis.Redis = Depends(get_redis)) -> RedisCacheManager:
    return RedisCacheManager(redis)


def get_user_variable_manager(
    user_variable_storage: UserVariableStorage = Depends(UserVariableStorage),
    agent_storage: AgentFlowSpecStorage = Depends(AgentFlowSpecStorage),
) -> UserVariableManager:
    return UserVariableManager(user_variable_storage, agent_storage)


def get_skill_manager() -> SkillManager:
    """Get the skill manager instance."""
    return SkillManager(SkillConfigStorage())


def get_agent_manager(
    storage: AgentFlowSpecStorage = Depends(AgentFlowSpecStorage),
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
    skill_storage: SkillConfigStorage = Depends(SkillConfigStorage),
) -> AgentManager:
    return AgentManager(storage, user_variable_manager, skill_storage)


def get_agency_manager(
    agent_manager: AgentManager = Depends(get_agent_manager),
    agency_config_storage: AgencyConfigStorage = Depends(AgencyConfigStorage),
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
) -> AgencyManager:
    return AgencyManager(agent_manager, agency_config_storage, user_variable_manager)


def get_session_manager(
    session_storage: SessionConfigStorage = Depends(SessionConfigStorage),
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
    session_adapter: SessionAdapter = Depends(get_session_adapter),
) -> SessionManager:
    """Returns a SessionManager object"""
    return SessionManager(
        session_storage=session_storage,
        user_variable_manager=user_variable_manager,
        session_adapter=session_adapter,
    )


def get_message_manager(
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
) -> MessageManager:
    return MessageManager(user_variable_manager)


def get_websocket_handler(
    connection_manager: WebSocketConnectionManager = Depends(WebSocketConnectionManager),
    auth_service: AuthService = Depends(AuthService),
    agency_manager: AgencyManager = Depends(get_agency_manager),
    message_manager: MessageManager = Depends(get_message_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> WebSocketHandler:
    return WebSocketHandler(connection_manager, auth_service, agency_manager, message_manager, session_manager)


def get_user_profile_manager(
    user_profile_storage: UserProfileStorage = Depends(UserProfileStorage),
) -> UserProfileManager:
    """Returns user profile data"""
    return UserProfileManager(user_profile_storage)
