import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_skill_manager
from backend.models.auth import User
from backend.models.request_models import SkillExecutePostRequest
from backend.models.response_models import (
    ExecuteSkillResponse,
    GetSkillResponse,
    SkillListResponse,
)
from backend.models.skill_config import SkillConfig
from backend.services.skill_executor import SkillExecutor
from backend.services.skill_manager import SkillManager

logger = logging.getLogger(__name__)

skill_router = APIRouter(tags=["skill"])


@skill_router.get("/skill/list")
async def get_skill_list(
    current_user: Annotated[User, Depends(get_current_user)],
    manager: SkillManager = Depends(get_skill_manager),
) -> SkillListResponse:
    """Get a list of configs for the skills the current user has access to."""
    skills = manager.get_skill_list(current_user.id)
    return SkillListResponse(data=skills)


@skill_router.get("/skill")
async def get_skill_config(
    current_user: Annotated[User, Depends(get_current_user)],
    id: str = Query(..., description="The unique identifier of the skill"),
    manager: SkillManager = Depends(get_skill_manager),
) -> GetSkillResponse:
    """Get a skill configuration by ID.
    NOTE: currently this endpoint is not used in the frontend.
    """
    config = manager.get_skill_config(id)
    manager.check_user_permissions(config, current_user.id)
    return GetSkillResponse(data=config)


@skill_router.put("/skill")
async def create_or_update_skill(
    current_user: Annotated[User, Depends(get_current_user)],
    config: SkillConfig = Body(...),
    manager: SkillManager = Depends(get_skill_manager),
) -> SkillListResponse:
    """Create or update a skill configuration.
    The skill will be automatically evaluated for safety using o1-mini.
    If approved, it will be immediately available for use.
    If not approved, an error message will explain why.
    Note: Skills are limited to 200 lines of code (this is a reliability limitation of o1-mini)."""
    manager.create_or_update_skill(config, current_user.id)
    configs = manager.get_skill_list(current_user.id)
    return SkillListResponse(data=configs, message=f"Skill {config.title} created or updated")


@skill_router.delete("/skill")
async def delete_skill(
    current_user: Annotated[User, Depends(get_current_user)],
    id: str = Query(..., description="The unique identifier of the skill"),
    manager: SkillManager = Depends(get_skill_manager),
):
    """Delete a skill configuration."""
    manager.delete_skill(id, current_user.id)
    configs = manager.get_skill_list(current_user.id)
    return SkillListResponse(data=configs, message="Skill configuration deleted")


@skill_router.post("/skill/execute")
async def execute_skill(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: SkillExecutePostRequest = Body(...),
    manager: SkillManager = Depends(get_skill_manager),
    executor: SkillExecutor = Depends(SkillExecutor),
) -> ExecuteSkillResponse:
    """Execute a skill by using the user prompt as input to GPT-4, which fills in the skill kwargs.
    The skill is executed in a secure E2B sandbox.
    Returns the output of the skill."""
    config = manager.get_skill_config(payload.id)
    manager.check_user_permissions(config, current_user.id)

    # check if the current_user has permissions to execute the skill
    if config.user_id:
        manager.check_user_permissions(config, current_user.id)

    # Execute the skill in a secure sandbox
    output = await executor.execute_skill(config.title, payload.user_prompt)

    return ExecuteSkillResponse(data=output)
