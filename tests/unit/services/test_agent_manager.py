from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.exceptions import NotFoundError
from backend.models.agent_flow_spec import AgentFlowSpec
from backend.models.skill_config import SkillConfig
from backend.services.agent_manager import AgentManager
from tests.testing_utils import TEST_USER_ID
from tests.testing_utils.constants import TEST_AGENT_ID


@pytest.fixture(autouse=True)
def mock_skill_registry():
    with patch("backend.services.agent_manager.skill_registry") as mock:
        mock.is_registered.side_effect = lambda x: x in {"GenerateProposal", "SearchWeb"}
        yield mock


@pytest.fixture
def storage_mock():
    return MagicMock()


@pytest.fixture
def user_variable_manager_mock():
    return MagicMock()


@pytest.fixture
def skill_storage_mock():
    return MagicMock()


@pytest.fixture
def agent_manager(storage_mock, user_variable_manager_mock, skill_storage_mock):
    return AgentManager(storage_mock, user_variable_manager_mock, skill_storage_mock)


@pytest.mark.asyncio
async def test_get_agent_list(agent_manager, storage_mock):
    user_configs = [AgentFlowSpec(user_id=TEST_USER_ID, config={"name": "Agent1"})]
    template_configs = [AgentFlowSpec(user_id=None, config={"name": "Agent2"})]
    storage_mock.load_by_user_id.side_effect = [user_configs, template_configs]

    result = await agent_manager.get_agent_list(TEST_USER_ID)

    assert result == template_configs + user_configs
    storage_mock.load_by_user_id.assert_any_call(TEST_USER_ID)
    storage_mock.load_by_user_id.assert_any_call(None)


@pytest.mark.asyncio
async def test_handle_agent_creation_or_update_new_agent(agent_manager, skill_storage_mock):
    config = AgentFlowSpec(config={"name": "Agent1"}, skills=["GenerateProposal"])
    skill_storage_mock.load_by_titles.return_value = [SkillConfig(title="GenerateProposal")]
    agent_manager._create_or_update_agent = AsyncMock(return_value="new_agent_id")

    result = await agent_manager.handle_agent_creation_or_update(config, TEST_USER_ID)

    assert result == "new_agent_id"
    assert config.user_id == TEST_USER_ID
    skill_storage_mock.load_by_titles.assert_called_once_with(config.skills)
    agent_manager._create_or_update_agent.assert_awaited_once_with(config)


@pytest.mark.asyncio
async def test_handle_agent_creation_or_update_existing_agent(agent_manager, storage_mock, skill_storage_mock):
    config = AgentFlowSpec(
        id=TEST_AGENT_ID, config={"name": "Agent1"}, skills=["GenerateProposal"], user_id=TEST_USER_ID
    )
    config_db = AgentFlowSpec(id=TEST_AGENT_ID, user_id=TEST_USER_ID, config={"name": "Agent1"})
    storage_mock.load_by_id.return_value = config_db
    skill_storage_mock.load_by_titles.return_value = [SkillConfig(title="GenerateProposal")]
    agent_manager._create_or_update_agent = AsyncMock(return_value="new_agent_id")

    result = await agent_manager.handle_agent_creation_or_update(config, TEST_USER_ID)

    assert result == "new_agent_id"
    storage_mock.load_by_id.assert_called_once_with(config.id)
    skill_storage_mock.load_by_titles.assert_called_once_with(config.skills)
    agent_manager._create_or_update_agent.assert_awaited_once_with(config)


@pytest.mark.asyncio
async def test_delete_agent(agent_manager, storage_mock):
    config = AgentFlowSpec(id=TEST_AGENT_ID, user_id=TEST_USER_ID, config={"name": "Agent1"})
    storage_mock.load_by_id.return_value = config
    agent_manager._openai_client = MagicMock()

    await agent_manager.delete_agent(TEST_AGENT_ID, TEST_USER_ID)

    storage_mock.load_by_id.assert_called_once_with(TEST_AGENT_ID)
    storage_mock.delete.assert_called_once_with(TEST_AGENT_ID)
    agent_manager._openai_client.beta.assistants.delete.assert_called_once_with(
        assistant_id=TEST_AGENT_ID, timeout=30.0
    )


@pytest.mark.asyncio
async def test_delete_agent_not_found(agent_manager, storage_mock):
    storage_mock.load_by_id.return_value = None

    with pytest.raises(NotFoundError, match=f"Agent not found: {TEST_AGENT_ID}") as exc_info:
        await agent_manager.delete_agent(TEST_AGENT_ID, TEST_USER_ID)

    assert str(exc_info.value) == f"Agent not found: {TEST_AGENT_ID}"


@pytest.mark.asyncio
async def test_delete_agent_forbidden(agent_manager, storage_mock):
    config = AgentFlowSpec(id=TEST_AGENT_ID, user_id="user2", config={"name": "Agent1"})
    storage_mock.load_by_id.return_value = config

    with pytest.raises(HTTPException) as exc_info:
        await agent_manager.delete_agent(TEST_AGENT_ID, TEST_USER_ID)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "You don't have permissions to access this agent"


# Test get_agent_list with owned_by_user=True
@pytest.mark.asyncio
async def test_get_agent_list_owned_by_user(agent_manager, storage_mock):
    user_configs = [AgentFlowSpec(user_id=TEST_USER_ID, config={"name": "Agent1"})]
    storage_mock.load_by_user_id.return_value = user_configs

    result = await agent_manager.get_agent_list(TEST_USER_ID, owned_by_user=True)

    assert result == user_configs
    storage_mock.load_by_user_id.assert_called_once_with(TEST_USER_ID)


# Test get_agent with existing agent
@pytest.mark.asyncio
async def test_get_agent_existing(agent_manager, storage_mock):
    config = AgentFlowSpec(id=TEST_AGENT_ID, user_id=TEST_USER_ID, config={"name": "Agent1"})
    storage_mock.load_by_id.return_value = config
    agent_manager._construct_agent = MagicMock(return_value="mocked_agent")

    result = await agent_manager.get_agent(TEST_AGENT_ID)

    assert result == ("mocked_agent", config)
    storage_mock.load_by_id.assert_called_once_with(TEST_AGENT_ID)
    agent_manager._construct_agent.assert_called_once_with(config)


# Test get_agent with non-existing agent
@pytest.mark.asyncio
async def test_get_agent_non_existing(agent_manager, storage_mock):
    storage_mock.load_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Agent not found: sender_agent_id"):
        await agent_manager.get_agent(TEST_AGENT_ID)

    storage_mock.load_by_id.assert_called_once_with(TEST_AGENT_ID)


# Test handle_agent_creation_or_update with non-existing agent and invalid skills
@pytest.mark.asyncio
async def test_handle_agent_creation_or_update_invalid_skills(agent_manager, skill_storage_mock):
    config = AgentFlowSpec(config={"name": "Agent1"}, skills=["InvalidSkill"])
    skill_storage_mock.load_by_titles.return_value = []

    with pytest.raises(HTTPException) as exc_info:
        await agent_manager.handle_agent_creation_or_update(config, TEST_USER_ID)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Some skills are not supported: {'InvalidSkill'}"
    skill_storage_mock.load_by_titles.assert_called_once_with(config.skills)


# Test handle_agent_creation_or_update with existing agent and invalid name
@pytest.mark.asyncio
async def test_handle_agent_creation_or_update_invalid_name(agent_manager, storage_mock, skill_storage_mock):
    config = AgentFlowSpec(
        id=TEST_AGENT_ID, config={"name": "Agent2"}, skills=["GenerateProposal"], user_id=TEST_USER_ID
    )
    config_db = AgentFlowSpec(id=TEST_AGENT_ID, user_id=TEST_USER_ID, config={"name": "Agent1"})
    storage_mock.load_by_id.return_value = config_db
    skill_storage_mock.load_by_titles.return_value = [SkillConfig(title="GenerateProposal")]

    with pytest.raises(HTTPException) as exc_info:
        await agent_manager.handle_agent_creation_or_update(config, TEST_USER_ID)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Renaming agents is not supported yet"
    storage_mock.load_by_id.assert_called_once_with(config.id)


# Test _create_or_update_agent
@pytest.mark.asyncio
async def test_create_or_update_agent(agent_manager, storage_mock):
    config = AgentFlowSpec(config={"name": "Agent1"}, user_id=TEST_USER_ID)
    agent_manager._construct_agent = MagicMock(return_value=MagicMock(id="new_agent_id"))

    result = await agent_manager._create_or_update_agent(config)

    assert result == "new_agent_id"
    assert config.config.name == f"Agent1 ({TEST_USER_ID})"
    agent_manager._construct_agent.assert_called_once_with(config)
    storage_mock.save.assert_called_once_with(config)


# Test _validate_agent_ownership with valid ownership
def test_validate_agent_ownership_valid(agent_manager):
    config_db = AgentFlowSpec(user_id=TEST_USER_ID, config={"name": "Agent1"})

    agent_manager._validate_agent_ownership(config_db, TEST_USER_ID)

    # No exception should be raised


# Test _validate_agent_name with valid name
def test_validate_agent_name_valid(agent_manager):
    config = AgentFlowSpec(config={"name": "Agent1"})
    config_db = AgentFlowSpec(config={"name": "Agent1"})

    agent_manager._validate_agent_name(config, config_db)

    # No exception should be raised
