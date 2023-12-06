import asyncio
import logging

from agency_swarm import Agency
from agency_swarm.util.oai import get_openai_client

from base_agency.config import load_agency_from_config

client = get_openai_client()

logger = logging.getLogger(__name__)


class AgencyManager:
    def __init__(self):
        self.active_agencies = {}  # agency_id: agency

    def get_agency(self, agency_id: str) -> Agency | None:
        """Get the agency for the given session ID"""
        if agency_id in self.active_agencies:
            return self.active_agencies[agency_id]
        return None

    async def create_agency(self, agency_id: str) -> Agency:
        """Create the agency for the given session ID"""
        start = asyncio.get_event_loop().time()

        agency = await asyncio.to_thread(load_agency_from_config, agency_id)
        self.active_agencies[agency_id] = agency

        end = asyncio.get_event_loop().time()
        logger.info(f"Agency creation took {end - start} seconds. Session ID: {agency_id}")
        return agency


if __name__ == "__main__":
    agency_manager = AgencyManager()
    agency_1 = asyncio.run(agency_manager.create_agency("test"))
    agency_2 = agency_manager.get_agency("test")
    assert agency_1 == agency_2

    agency_1.run_demo()
