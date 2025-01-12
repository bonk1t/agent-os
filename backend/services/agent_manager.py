import asyncio
import logging
from datetime import UTC, datetime
from http import HTTPStatus

from agency_swarm import Agent
from fastapi import HTTPException

from backend.constants import DEFAULT_OPENAI_API_TIMEOUT
from backend.custom_skills import skill_registry
from backend.exceptions import NotFoundError
from backend.models.agent_flow_spec import AgentFlowSpec
from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.services.oai_client import get_openai_client
from backend.services.user_variable_manager import UserVariableManager

logger = logging.getLogger(__name__)


class AgentManager:
    def __init__(
        self,
        storage: AgentFlowSpecStorage,
        user_variable_manager: UserVariableManager,
        skill_storage: SkillConfigStorage,
    ) -> None:
        self.user_variable_manager = user_variable_manager
        self.storage = storage
        self.skill_storage = skill_storage
        self._openai_client = None

    @property
    def openai_client(self):
        """Lazily get the OpenAI client."""
        if self._openai_client is None:
            self._openai_client = get_openai_client(self.user_variable_manager)
        return self._openai_client

    async def get_agent_list(self, user_id: str, owned_by_user: bool = False) -> list[AgentFlowSpec]:
        user_configs = self.storage.load_by_user_id(user_id)
        template_configs = self.storage.load_by_user_id(None) if not owned_by_user else []
        agents = user_configs + template_configs
        sorted_agents = sorted(agents, key=lambda x: x.timestamp, reverse=True)
        return sorted_agents

    async def get_agent(self, agent_id: str) -> tuple[Agent, AgentFlowSpec]:
        config = self.storage.load_by_id(agent_id)
        if not config:
            raise NotFoundError("Agent", agent_id)
        agent = await asyncio.to_thread(self._construct_agent, config)
        return agent, config

    async def handle_agent_creation_or_update(self, config: AgentFlowSpec, current_user_id: str) -> str:
        """Create or update an agent. If the agent already exists, it will be updated."""
        # Support template configs
        if not config.user_id:
            logger.info(f"Creating agent for user: {current_user_id}, agent: {config.config.name}")
            config.id = None

        # Check permissions and validate agent name
        if config.id:
            config_db = self.storage.load_by_id(config.id)
            if not config_db:
                raise NotFoundError("Agent", config.id)
            self._validate_agent_ownership(config_db, current_user_id)
            self._validate_agent_name(config, config_db)

        # Ensure the agent is associated with the current user
        config.user_id = current_user_id
        config.timestamp = datetime.now(UTC).isoformat()

        # Validate skills
        self._validate_skills(config.skills)

        return await self._create_or_update_agent(config)

    async def delete_agent(self, agent_id: str, current_user_id: str) -> None:
        config = self.storage.load_by_id(agent_id)
        if not config:
            raise NotFoundError("Agent", agent_id)
        self._validate_agent_ownership(config, current_user_id)
        self.storage.delete(agent_id)

        self.openai_client.beta.assistants.delete(assistant_id=agent_id, timeout=DEFAULT_OPENAI_API_TIMEOUT)

    async def _create_or_update_agent(self, config: AgentFlowSpec) -> str:
        """Create or update an agent. If the agent already exists, it will be updated."""
        # FIXME: a workaround explained at the top of the file api/agent.py
        if not config.config.name.endswith(f" ({config.user_id})"):
            config.config.name = f"{config.config.name} ({config.user_id})"

        agent = await asyncio.to_thread(self._construct_agent, config)
        await asyncio.to_thread(agent.init_oai)  # initialize the openai agent to get the id
        config.id = agent.id
        self.storage.save(config)
        return agent.id

    def _construct_agent(self, agent_flow_spec: AgentFlowSpec) -> Agent:
        agent = Agent(
            id=agent_flow_spec.id,
            name=agent_flow_spec.config.name,
            description=agent_flow_spec.description,
            instructions=agent_flow_spec.config.system_message,
            files_folder=agent_flow_spec.config.code_execution_config.work_dir,
            tools=[skill_registry.get_skill(skill) for skill in agent_flow_spec.skills],
            temperature=agent_flow_spec.config.temperature,
            model=agent_flow_spec.config.model,
        )
        return agent

    @staticmethod
    def _validate_agent_ownership(config_db: AgentFlowSpec, current_user_id: str) -> None:
        if config_db.user_id != current_user_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="You don't have permissions to access this agent"
            )

    @staticmethod
    def _validate_agent_name(config: AgentFlowSpec, config_db: AgentFlowSpec) -> None:
        if config.config.name != config_db.config.name:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Renaming agents is not supported yet")

    def _validate_skills(self, skills: list[str]) -> None:
        # Check if all skills are supported
        available_skills = self.skill_storage.load_by_titles(skills)
        available_skill_titles = {skill.title for skill in available_skills}
        unsupported_skills = {skill for skill in skills if skill not in available_skill_titles}
        if unsupported_skills:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=f"Some skills are not supported: {unsupported_skills}"
            )
