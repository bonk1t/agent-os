from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.params import Query
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from nalgonda.dependencies.auth import get_current_active_user
from nalgonda.dependencies.dependencies import get_agent_manager
from nalgonda.models.agent_config import AgentConfig
from nalgonda.models.auth import UserInDB
from nalgonda.persistence.agent_config_firestore_storage import AgentConfigFirestoreStorage
from nalgonda.services.agent_manager import AgentManager

agent_router = APIRouter(tags=["agent"])


@agent_router.get("/agent")
async def get_agent_list(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    storage: AgentConfigFirestoreStorage = Depends(AgentConfigFirestoreStorage),
) -> list[AgentConfig]:
    agents = storage.load_by_user_id(current_user.id)
    return agents


@agent_router.get("/agent/config")
async def get_agent_config(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    agent_id: str = Query(..., description="The unique identifier of the agent"),
    storage: AgentConfigFirestoreStorage = Depends(AgentConfigFirestoreStorage),
) -> AgentConfig:
    agent_config = storage.load_by_agent_id(agent_id)
    if not agent_config:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent configuration not found")
    # check if the current user is the owner of the agent
    if agent_config.owner_id != current_user.id:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")
    return agent_config


@agent_router.put("/agent/config")
async def update_agent_config(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    agent_config: AgentConfig = Body(...),
    agent_manager: AgentManager = Depends(get_agent_manager),
    storage: AgentConfigFirestoreStorage = Depends(AgentConfigFirestoreStorage),
) -> dict[str, str]:
    # check if the current user is the owner of the agent
    if agent_config.agent_id:
        agent_config_db = storage.load_by_agent_id(agent_config.agent_id)
        if not agent_config_db:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent configuration not found")
        if agent_config_db.owner_id != current_user.id:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Forbidden")

    # Ensure the agent is associated with the current user
    agent_config.owner_id = current_user.id

    agent_id = await agent_manager.create_or_update_agent(agent_config)
    return {"agent_id": agent_id}
