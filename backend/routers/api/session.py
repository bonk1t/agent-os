import logging
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.params import Query

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_agency_manager, get_session_manager
from backend.models.auth import User
from backend.models.request_models import RenameSessionRequest
from backend.models.response_models import CreateSessionResponse, SessionListResponse
from backend.services.agency_manager import AgencyManager
from backend.services.session_manager import SessionManager
from backend.utils import sanitize_id

logger = logging.getLogger(__name__)

session_router = APIRouter(
    responses={404: {"description": "Not found"}},
    tags=["session"],
)


@session_router.get("/session/list")
async def get_session_list(
    current_user: Annotated[User, Depends(get_current_user)],
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """Return a list of all sessions for the current user."""
    sessions_for_api = session_manager.get_sessions_for_user(current_user.id)
    return SessionListResponse(data=sessions_for_api)


@session_router.post("/session")
async def create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    agency_id: str = Query(..., description="The unique identifier of the agency"),
    agency_manager: AgencyManager = Depends(get_agency_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> CreateSessionResponse:
    """Create a new session for the given agency and return a list of all sessions for the current user."""
    logger.info(f"Creating a new session for the agency: {agency_id}, and user: {current_user.id}")

    new_thread_ids: dict[str, Any] = {}
    agency, agency_config = await agency_manager.get_agency(
        agency_id, thread_ids=new_thread_ids, user_id=current_user.id
    )

    session_id = session_manager.create_session(
        agency, name=agency_config.name, agency_id=agency_id, user_id=current_user.id, thread_ids=new_thread_ids
    )

    sessions_for_api = session_manager.get_sessions_for_user(current_user.id)
    return CreateSessionResponse(data=sessions_for_api, session_id=session_id, message="Session created successfully")


@session_router.post("/session/rename")
async def rename_session(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: RenameSessionRequest = Body(...),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """Rename the session with the given id and return a list of all sessions for the current user."""
    session_id = sanitize_id(payload.id)
    logger.info(f"Renaming session: {session_id}, user: {current_user.id}")

    db_session = session_manager.get_session(session_id)
    session_manager.validate_session_ownership(db_session.user_id, current_user.id)
    session_manager.rename_session(session_id, payload.name)

    sessions_for_api = session_manager.get_sessions_for_user(current_user.id)
    return SessionListResponse(message="Session renamed successfully", data=sessions_for_api)


@session_router.delete("/session")
async def delete_session(
    current_user: Annotated[User, Depends(get_current_user)],
    id: str = Query(..., description="The unique identifier of the session"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """Delete the session with the given id and return a list of all sessions for the current user."""
    logger.info(f"Deleting session: {id}, user: {current_user.id}")

    session_manager.delete_session(id)

    sessions_for_api = session_manager.get_sessions_for_user(current_user.id)
    return SessionListResponse(message="Session deleted successfully", data=sessions_for_api)
