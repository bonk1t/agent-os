import logging
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_agency_manager, get_session_manager
from backend.models.auth import User
from backend.models.response_models import BaseResponse, SessionListResponse
from backend.repositories.agency_config_storage import AgencyConfigStorage
from backend.repositories.session_storage import SessionConfigStorage
from backend.services.agency_manager import AgencyManager
from backend.services.context_vars_manager import ContextEnvVarsManager
from backend.services.session_manager import SessionManager

logger = logging.getLogger(__name__)
session_router = APIRouter(
    responses={404: {"description": "Not found"}},
    tags=["session"],
)


@session_router.get("/session/list")
async def get_session_list(
    current_user: Annotated[User, Depends(get_current_user)],
    session_storage: SessionConfigStorage = Depends(SessionConfigStorage),
) -> SessionListResponse:
    """Return a list of all sessions for the current user."""
    session_configs = session_storage.load_by_user_id(current_user.id)
    return SessionListResponse(data=session_configs)


@session_router.post("/session")
async def create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    agency_id: str = Query(..., description="The unique identifier of the agency"),
    agency_manager: AgencyManager = Depends(get_agency_manager),
    agency_storage: AgencyConfigStorage = Depends(AgencyConfigStorage),
    session_storage: SessionConfigStorage = Depends(SessionConfigStorage),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """Create a new session for the given agency and return a list of all sessions for the current user."""
    # check if the current_user has permissions to create a session for the agency
    agency_config_db = agency_storage.load_by_id(agency_id)
    if not agency_config_db:
        logger.warning(f"Agency not found: {agency_id}, user: {current_user.id}")
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Agency not found")
    if agency_config_db.user_id != current_user.id:
        logger.warning(
            f"User {current_user.id} does not have permissions to create a session for the agency: {agency_id}"
        )
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Forbidden")

    # Set the user_id in the context variables
    ContextEnvVarsManager.set("user_id", current_user.id)

    logger.info(f"Creating a new session for the agency: {agency_id}, and user: {current_user.id}")

    agency = await agency_manager.get_agency(agency_id, None)
    if not agency:
        logger.warning(f"Agency not found: {agency_id}, user: {current_user.id}")
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Agency not found")

    session_id = session_manager.create_session(agency, agency_id=agency_id, user_id=current_user.id)

    await agency_manager.cache_agency(agency, agency_id, session_id)

    session_configs = session_storage.load_by_user_id(current_user.id)
    return SessionListResponse(data=session_configs)


@session_router.delete("/session")
async def delete_session(
    current_user: Annotated[User, Depends(get_current_user)],
    id: str = Query(..., description="The unique identifier of the session"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> BaseResponse:
    """Delete the session with the given id."""
    logger.info(f"Deleting session: {id}, user: {current_user.id}")
    session_manager.delete_session(id)
    return BaseResponse(message="Session deleted successfully")
