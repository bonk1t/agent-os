import logging
import uuid

from agency_manager import AgencyManager
from agency_swarm import Agency
from fastapi import APIRouter
from models.request_models import AgencyMessagePostRequest

logger = logging.getLogger(__name__)
agency_manager = AgencyManager()

agency_api_router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@agency_api_router.post("/")
async def create_agency():
    """Create a new agency and return its id."""
    # TODO: Add authentication: check if user is logged in and has permission to create an agency

    agency_id = uuid.uuid4().hex
    await agency_manager.get_or_create_agency(agency_id)
    return {"agency_id": agency_id}


@agency_api_router.post("/message")
async def send_message(payload: AgencyMessagePostRequest) -> dict:
    """Send a message to the CEO of the given agency."""
    # TODO: Add authentication: check if agency_id is valid for the given user

    logger.info(f"Received message: {payload.message} for agency: {payload.agency_id}")
    agency = await agency_manager.get_or_create_agency(agency_id=payload.agency_id)

    try:
        response = await process_message(payload.message, agency)
        return {"response": response}
    except Exception as e:
        logger.exception(e)
        return {"error": str(e)}


async def process_message(user_message: str, agency: Agency) -> str:
    """Process a message from the user and return the response from the CEO."""
    response = agency.get_completion(message=user_message, yield_messages=False)
    return response
