import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.params import Query

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_agency_manager, get_agent_adapter, get_agent_manager
from backend.models.agent_flow_spec import AgentFlowSpecForAPI
from backend.models.auth import User
from backend.models.response_models import (
    AgentListResponse,
    GetAgentResponse,
)
from backend.services.adapters.agent_adapter import AgentAdapter
from backend.services.agency_manager import AgencyManager
from backend.services.agent_manager import AgentManager

logger = logging.getLogger(__name__)

agent_router = APIRouter(tags=["agent"])


# FIXME: agent name should be unique (agency-swarm gets it by name from settings.json).
# The current workaround: we append the user_id to the agent name to make it unique.
# Renaming is not supported yet.


@agent_router.get("/agent/list")
async def get_agent_list(
    current_user: Annotated[User, Depends(get_current_user)],
    adapter: Annotated[AgentAdapter, Depends(get_agent_adapter)],
    manager: AgentManager = Depends(get_agent_manager),
    owned_by_user: bool = Query(False, description="Filter agents owned by the current user"),
) -> AgentListResponse:
    """Get a list of agent configurations."""
    configs = await manager.get_agent_list(current_user.id, owned_by_user=owned_by_user)
    configs_for_api = [adapter.to_api(config) for config in configs]
    return AgentListResponse(data=configs_for_api)


@agent_router.get("/agent")
async def get_agent_config(
    current_user: Annotated[User, Depends(get_current_user)],
    adapter: Annotated[AgentAdapter, Depends(get_agent_adapter)],
    id: str = Query(..., description="The unique identifier of the agent"),
    manager: AgentManager = Depends(get_agent_manager),
) -> GetAgentResponse:
    """Get the configuration of a specific agent.
    NOTE: currently this endpoint is not used in the frontend.
    """
    _, config = await manager.get_agent(id)
    # check if the current user is the owner of the agent
    if config.user_id and config.user_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="You don't have permissions to access this agent")
    config_for_api = adapter.to_api(config)
    return GetAgentResponse(data=config_for_api)


@agent_router.put("/agent")
async def create_or_update_agent(
    current_user: Annotated[User, Depends(get_current_user)],
    adapter: Annotated[AgentAdapter, Depends(get_agent_adapter)],
    config: AgentFlowSpecForAPI = Body(...),
    manager: AgentManager = Depends(get_agent_manager),
) -> AgentListResponse:
    """Create or update an agent configuration."""
    # Transform the API model to the internal model
    internal_config = adapter.to_model(config)

    await manager.handle_agent_creation_or_update(internal_config, current_user.id)

    configs = await manager.get_agent_list(current_user.id)
    configs_for_api = [adapter.to_api(config) for config in configs]
    return AgentListResponse(message="Saved", data=configs_for_api)


@agent_router.delete("/agent")
async def delete_agent(
    current_user: Annotated[User, Depends(get_current_user)],
    adapter: Annotated[AgentAdapter, Depends(get_agent_adapter)],
    id: str = Query(..., description="The unique identifier of the agent"),
    agency_manager: AgencyManager = Depends(get_agency_manager),
    manager: AgentManager = Depends(get_agent_manager),
) -> AgentListResponse:
    """Delete an agent configuration."""
    # Check if the agent is part of any team configurations
    if agency_manager.is_agent_used_in_agencies(id):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Agent cannot be deleted as it is currently used in a team configuration",
        )

    await manager.delete_agent(id, current_user.id)

    configs = await manager.get_agent_list(current_user.id)
    configs_for_api = [adapter.to_api(config) for config in configs]
    return AgentListResponse(message="Agent configuration deleted", data=configs_for_api)
