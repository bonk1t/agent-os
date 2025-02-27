from unittest.mock import AsyncMock, MagicMock, patch
import json
import pytest
import pytest_asyncio

from backend.models.skill_config import SkillConfig
from backend.services.skill_executor import SkillExecutor


def test_get_skill_class_found():
    skill_name = "SummarizeCode"
    mock_skill = MagicMock()

    with patch("backend.custom_skills.SKILL_MAPPING", {skill_name: mock_skill}):
        service = SkillExecutor()
        result = service._get_skill_class(skill_name)
        assert result == mock_skill, "The function did not return the correct skill class"


def test_get_skill_class_not_found():
    skill_name = "NonExistingSkill"
    with patch("backend.custom_skills.SKILL_MAPPING", {}):
        service = SkillExecutor()
        with pytest.raises(RuntimeError) as exc_info:
            service._get_skill_class(skill_name)
        assert "Skill not found: NonExistingSkill" in str(exc_info.value)


def test_get_skill_arguments():
    with patch("backend.services.skill_executor.get_chat_completion", return_value='{"arg": "value"}') as mock_get_chat:
        service = SkillExecutor()
        result = service._get_skill_arguments("function_spec", "user_prompt")
        expected_args_str = '{"arg": "value"}'
        assert result == expected_args_str, "The function did not return the expected argument string"
        mock_get_chat.assert_called_once()


@pytest.fixture
def mock_skill_config():
    return SkillConfig(
        id="skill1",
        user_id="user1",
        title="TestSkill",
        description="Test skill for unit tests",
        content="class TestSkill(BaseTool):\n    def run(self):\n        return 'Success'",
    )


@pytest_asyncio.fixture
async def mock_sandbox_manager():
    with patch("backend.services.skill_executor.sandbox_manager") as mock:
        mock.execute_skill_from_config = AsyncMock(return_value="Sandbox execution result")
        yield mock


@pytest.mark.asyncio
async def test_execute_skill_in_sandbox_success(mock_skill_config, mock_sandbox_manager):
    args = {"arg": "value"}
    
    service = SkillExecutor()
    result = await service._execute_skill_in_sandbox(mock_skill_config, args)
    
    assert result == "Sandbox execution result"
    mock_sandbox_manager.execute_skill_from_config.assert_called_once_with(
        mock_skill_config, args, {"OPENAI_API_KEY": None}
    )


@pytest.mark.asyncio
async def test_execute_skill_in_sandbox_failure(mock_skill_config):
    args = {"arg": "value"}
    error_msg = "Sandbox execution error"
    
    with patch("backend.services.skill_executor.sandbox_manager") as mock:
        mock.execute_skill_from_config = AsyncMock(side_effect=Exception(error_msg))
        
        service = SkillExecutor()
        result = await service._execute_skill_in_sandbox(mock_skill_config, args)
        
        assert f"Error: {error_msg}" in result


@pytest.mark.asyncio
async def test_execute_skill_success(mock_skill_config, mock_sandbox_manager):
    skill_name = "TestSkill"
    user_prompt = "Run the test skill"
    mock_skill_class = MagicMock()
    mock_skill_class.openai_schema = {"name": "TestSkill", "parameters": {}}
    
    with (
        patch("backend.services.skill_executor.SkillExecutor._get_skill_class", 
              return_value=mock_skill_class) as mock_get_class,
        patch("backend.services.skill_executor.SkillExecutor._get_skill_arguments", 
              return_value='{"arg": "value"}') as mock_get_args,
        patch.object(SkillExecutor, "skill_config_storage") as mock_storage,
    ):
        mock_storage.load_by_titles.return_value = [mock_skill_config]
        
        service = SkillExecutor()
        result = await service.execute_skill(skill_name, user_prompt)
        
        assert result == "Sandbox execution result"
        mock_get_class.assert_called_once_with(skill_name)
        mock_get_args.assert_called_once()
        mock_storage.load_by_titles.assert_called_once_with([skill_name])
        mock_sandbox_manager.execute_skill_from_config.assert_called_once_with(
            mock_skill_config, json.loads('{"arg": "value"}'), {"OPENAI_API_KEY": None}
        )


@pytest.mark.asyncio
async def test_execute_skill_not_found_in_storage():
    skill_name = "TestSkill"
    user_prompt = "Run the test skill"
    mock_skill_class = MagicMock()
    
    with (
        patch("backend.services.skill_executor.SkillExecutor._get_skill_class", 
              return_value=mock_skill_class) as mock_get_class,
        patch.object(SkillExecutor, "skill_config_storage") as mock_storage,
    ):
        mock_storage.load_by_titles.return_value = []
        
        service = SkillExecutor()
        result = await service.execute_skill(skill_name, user_prompt)
        
        assert f"Error: Skill {skill_name} not found in storage" in result
        mock_get_class.assert_called_once_with(skill_name)
        mock_storage.load_by_titles.assert_called_once_with([skill_name])
