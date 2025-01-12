import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.constants import INTERNAL_ERROR_MESSAGE
from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_agency_manager, get_message_manager, get_session_manager
from backend.models.auth import User
from backend.models.message import Message
from backend.models.response_models import MessagePostResponse
from backend.services.agency_manager import AgencyManager
from backend.services.context_vars_manager import ContextEnvVarsManager
from backend.services.message_manager import MessageManager
from backend.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

message_router = APIRouter(
    responses={404: {"description": "Not found"}},
    tags=["message"],
)


@message_router.get("/message/list")
async def get_message_list(
    current_user: Annotated[User, Depends(get_current_user)],
    session_id: str,
    limit: int = 20,
    before: str | None = None,
    message_manager: MessageManager = Depends(get_message_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> list[Message]:
    """Get the list of messages for the given session_id."""
    # check if the current_user has permissions to send a message to the agency
    session_config = session_manager.get_session(session_id)
    session_manager.validate_session_ownership(session_config.user_id, current_user.id)

    messages = message_manager.get_messages(session_id, limit=limit, before=before)
    return messages


@message_router.post("/message")
async def post_message(
    current_user: Annotated[User, Depends(get_current_user)],
    request: Message,
    agency_manager: AgencyManager = Depends(get_agency_manager),
    message_manager: MessageManager = Depends(get_message_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> MessagePostResponse:
    """Send a message to the User Proxy (the main agent) for the given agency_id and session_id."""
    session_id = request.session_id

    session_config = session_manager.get_session(session_id)
    agency_id = session_config.agency_id

    # Set the agency_id in the context variables
    ContextEnvVarsManager.set("agency_id", agency_id)

    logger.info(f"Received a message for agency_id: {agency_id}, session_id: {session_id}")

    # permissions are checked in the agency_manager.get_agency method
    agency, _ = await agency_manager.get_agency(
        agency_id, thread_ids=session_config.thread_ids, user_id=current_user.id
    )

    try:
        response = await asyncio.to_thread(
            agency.get_completion, message=request.content, yield_messages=False, message_files=None
        )
    except Exception as e:
        logger.exception(f"Error sending message to agency {agency_id}, session {session_id}")
        raise HTTPException(status_code=500, detail=INTERNAL_ERROR_MESSAGE) from e

    # update the session timestamp
    session_manager.update_session_timestamp(session_id)

    # get the updated list of messages for the session
    messages = message_manager.get_messages(session_id, limit=20)

    return MessagePostResponse(data=messages, response=response)
