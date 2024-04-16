import asyncio
import logging
from copy import copy
from datetime import UTC, datetime
from http import HTTPStatus

from agency_swarm import Agency, Agent
from fastapi import HTTPException

from backend.models.agency_config import AgencyConfig
from backend.repositories.agency_config_storage import AgencyConfigStorage
from backend.services.agent_manager import AgentManager
from backend.services.caching.redis_cache_manager import RedisCacheManager
from backend.services.oai_client import get_openai_client
from backend.services.user_secret_manager import UserSecretManager

logger = logging.getLogger(__name__)


class AgencyManager:
    def __init__(
        self,
        cache_manager: RedisCacheManager,
        agent_manager: AgentManager,
        agency_config_storage: AgencyConfigStorage,
        user_secret_manager: UserSecretManager,
    ) -> None:
        self.storage = agency_config_storage
        self.agent_manager = agent_manager
        self.cache_manager = cache_manager
        self.user_secret_manager = user_secret_manager

    async def get_agency_list(self, user_id: str) -> list[AgencyConfig]:
        """Get the list of agencies for the user. It will return the agencies for the user and the templates."""
        user_agencies = self.storage.load_by_user_id(user_id)
        template_agencies = self.storage.load_by_user_id(None)
        return user_agencies + template_agencies

    async def get_agency(self, id_: str, session_id: str | None = None) -> Agency | None:
        cache_key = self.get_cache_key(id_, session_id)
        agency = await self.cache_manager.get(cache_key)

        if not agency:
            # If agency is not found in the cache, re-populate the cache
            agency = await self.repopulate_cache_and_update_assistants(id_, session_id)
            if not agency:
                logger.error(f"Agency configuration for {id_} could not be found in the Firestore database.")
                return None

        agency = self._set_client_objects(agency)
        return agency

    async def handle_agency_creation_or_update(self, config: AgencyConfig, current_user_id: str) -> str:
        """Handle the agency creation or update. It will check the permissions and update the agency in the Firestore
        and the cache. It will also update the assistants."""
        # support template configs:
        if not config.user_id:
            logger.info(f"Creating agency for user: {current_user_id}, agency: {config.name}")
            config.id = None  # type: ignore

        # Check permissions
        if config.id:
            config_db = self.storage.load_by_id(config.id)
            if not config_db:
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Agency not found")
            self._validate_agency_ownership(config_db, current_user_id)
        await self._validate_agent_ownership(config.agents, current_user_id)

        # Ensure the agency is associated with the current user
        config.user_id = current_user_id
        config.timestamp = datetime.now(UTC).isoformat()

        return await self._update_or_create_agency(config)

    async def repopulate_cache_and_update_assistants(
        self, agency_id: str, session_id: str | None = None
    ) -> Agency | None:
        """Gets the agency config from the Firestore, constructs agents and agency
        (agency-swarm also updates assistants), and saves the Agency instance to Redis
        (with expiration period, see constants.DEFAULT_CACHE_EXPIRATION).
        Returns the cached Agency instance if successful, otherwise None.
        """
        agency_config = self.storage.load_by_id(agency_id)
        if not agency_config:
            logger.error(f"Agency with id {agency_id} not found.")
            return None

        agents = await self.load_and_construct_agents(agency_config)
        agency = await asyncio.to_thread(self.construct_agency, agency_config, agents)

        cached_agency = await self.cache_agency(agency, agency_id, session_id)
        return cached_agency

    async def load_and_construct_agents(self, agency_config: AgencyConfig) -> dict[str, Agent]:
        agents = {}
        for agent_id in agency_config.agents:
            get_result = await self.agent_manager.get_agent(agent_id)
            if get_result:
                agent, agent_flow_spec = get_result
                agents[agent_flow_spec.config.name] = agent
            else:
                logger.error(f"Agent with id {agent_id} not found.")
                # TODO: Handle this error (raise exception?)
        return agents

    @staticmethod
    def construct_agency(agency_config: AgencyConfig, agents: dict[str, Agent]) -> Agency:
        """Create the agency using external library agency-swarm. It is a wrapper around OpenAI API.
        It saves all the settings in the settings.json file (in the root folder, not thread safe)
        """
        agency_chart = []
        if agents and agency_config.main_agent:
            main_agent = agents[agency_config.main_agent]
            agency_chart = [main_agent]
            if agency_config.agency_chart:
                new_agency_chart = [[agents[name] for name in layer] for layer in agency_config.agency_chart.values()]
                agency_chart.extend(new_agency_chart)

        return Agency(agency_chart, shared_instructions=agency_config.shared_instructions)

    async def cache_agency(self, agency: Agency, agency_id: str, session_id: str | None) -> Agency:
        """Cache the agency."""
        cache_key = self.get_cache_key(agency_id, session_id)
        agency_clean = self._remove_client_objects(agency)
        await self.cache_manager.set(cache_key, agency_clean)
        return agency_clean

    async def delete_agency(self, agency_id: str) -> None:
        """Delete the agency from the Firestore and the cache."""
        self.storage.delete(agency_id)
        await self.delete_agency_from_cache(agency_id, None)

    async def delete_agency_from_cache(self, agency_id: str, session_id: str | None) -> None:
        """Delete the agency from the cache."""
        cache_key = self.get_cache_key(agency_id, session_id)
        await self.cache_manager.delete(cache_key)

    @staticmethod
    def get_cache_key(agency_id: str, session_id: str | None = None) -> str:
        return f"{agency_id}/{session_id}" if session_id else agency_id

    async def _update_or_create_agency(self, agency_config: AgencyConfig) -> str:
        """Update or create the agency. It will update the agency in the Firestore and also in the cache.
        repopulate_cache_and_update_assistants method call ensures that the assistants are up-to-date.
        """
        AgencyConfig.model_validate(agency_config.model_dump())
        id_ = self.storage.save(agency_config)
        await self.repopulate_cache_and_update_assistants(id_)
        return id_

    async def _validate_agent_ownership(self, agents: list[str], current_user_id: str) -> None:
        """Validate the agent ownership. It will check if the current user has permissions to use the agents."""
        # check that all used agents belong to the current user
        for agent_id in agents:
            agent_flow_spec = self.agent_manager.storage.load_by_id(agent_id)
            if not agent_flow_spec:
                raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"Agent not found: {agent_id}")
            if agent_flow_spec.user_id != current_user_id:
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN, detail=f"You don't have permissions to use agent {agent_id}"
                )
        # FIXME: current limitation: all agents must belong to the current user.
        # to fix: If the agent is a template (agent_flow_spec.user_id is None), it should be copied for the current user
        # (reuse the code from api/agent.py)

    @staticmethod
    def _validate_agency_ownership(config_db: AgencyConfig, current_user_id: str) -> None:
        """Validate the agency ownership. It will check if the current user has permissions to update the agency."""
        # check if the current_user has permissions
        if config_db.user_id != current_user_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="You don't have permissions to access this agency"
            )

    @staticmethod
    def _remove_client_objects(agency: Agency) -> Agency:
        """Remove all client objects from the agency object"""
        agency_copy = copy(agency)
        agency_copy.agents = [copy(agent) for agent in agency_copy.agents]

        for agent in agency_copy.agents:
            agent.client = None

        for agent in agency_copy.main_recipients:
            agent.client = None

        agency_copy.main_thread = copy(agency_copy.main_thread)
        agency_copy.main_thread.client = None

        if agency_copy.main_thread.recipient_agent:
            agency_copy.main_thread.recipient_agent = copy(agency_copy.main_thread.recipient_agent)
            agency_copy.main_thread.recipient_agent.client = None

        if agency_copy.ceo:
            agency_copy.ceo = copy(agency_copy.ceo)
            agency_copy.ceo.client = None

        return agency_copy

    def _set_client_objects(self, agency: Agency) -> Agency:
        """Restore all client objects within the agency object"""
        client = get_openai_client(user_secret_manager=self.user_secret_manager)
        # Restore client for each agent in the agency
        for agent in agency.agents:
            agent.client = client

        for agent in agency.main_recipients:
            agent.client = client

        # Restore client for the main thread
        agency.main_thread.client = client

        # Check and restore client for the recipient agent in the main thread, if it exists
        if agency.main_thread.recipient_agent:
            agency.main_thread.recipient_agent.client = client

        # Check and restore client for the CEO, if it exists
        if agency.ceo:
            agency.ceo.client = client

        return agency
