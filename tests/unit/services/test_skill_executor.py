import json
import os
from unittest.mock import MagicMock, patch

import pytest

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


@patch("backend.services.skill_executor.Sandbox")
def test_execute_skill_success(mock_sandbox):
    mock_sandbox_instance = mock_sandbox.return_value
    mock_sandbox_instance.run_code.return_value.logs.stdout = ["Skill output"]

    skill = MagicMock()
    skill.title = "TestSkill"
    skill.content = f"class TestSkill:\n    def __init__(self, arg):\n        self.arg = arg\n    def run(self):\n        return 'Skill output'"
    args = json.dumps({"arg": "value"})

    with patch.dict(os.environ, {"E2B_API_KEY": "test_api_key"}):
        service = SkillExecutor()
        result = service._execute_skill(skill, args)

    assert result == "Skill output", "The function did not execute the skill correctly or failed to return its output"


@patch("backend.services.skill_executor.Sandbox")
def test_execute_skill_failure(mock_sandbox):
    mock_sandbox_instance = mock_sandbox.return_value
    mock_sandbox_instance.run_code.side_effect = Exception("Error running skill")

    skill = MagicMock()
    skill.title = "TestSkill"
    skill.content = "class TestSkill:\n    def __init__(self, arg):\n        self.arg = arg\n    def run(self):\n        return 'Skill output'"
    args = json.dumps({"arg": "value"})

    with patch.dict(os.environ, {"E2B_API_KEY": "test_api_key"}):
        service = SkillExecutor()
        result = service._execute_skill(skill, args)

    assert "Error: Error running skill" in result, "The function did not handle exceptions from skill execution properly"
