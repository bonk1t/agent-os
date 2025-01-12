from unittest.mock import MagicMock, patch

import pytest

from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.services.skill_manager import SafetyEvaluation, SkillManager
from tests.testing_utils import TEST_USER_ID

VALID_SKILL_CODE = """
from agency_swarm import BaseTool

class TestSkill(BaseTool):
    def run(self):
        print("Hello World Updated")
        return "Success"
"""


@pytest.fixture
def skill_config_data():
    """Base skill configuration data for tests."""
    return {
        "id": "skill1",
        "user_id": TEST_USER_ID,
        "title": "Skill 1",
        "description": "",
        "timestamp": "2024-04-04T09:39:13.048457+00:00",
        "content": 'print("Hello World")',
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with predefined responses."""
    with patch("backend.utils.get_openai_client") as mock:
        mock_client = MagicMock()
        # Mock the chat completion response
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message = MagicMock()
        mock_completion.choices[0].message.content = '{"is_safe": true, "reason": "Safe code"}'
        mock_client.chat.completions.create.return_value = mock_completion

        # Mock the instructor parse response
        mock_parse = MagicMock()
        mock_parse.choices = [MagicMock()]
        mock_parse.choices[0].message = MagicMock()
        mock_parse.choices[0].message.parsed = SafetyEvaluation(is_safe=True, reason="Safe code")
        mock_client.chat.completions.parse.return_value = mock_parse

        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_skill_module():
    """Mock skill module with TestSkill class."""
    mock_module = MagicMock()
    mock_module.TestSkill = MagicMock()
    with (
        patch("importlib.import_module", return_value=mock_module),
        patch("importlib.reload", return_value=mock_module),
    ):
        yield mock_module


@pytest.fixture
def mock_skill_registry():
    """Mock skill registry with default behaviors."""
    with patch("backend.custom_skills.skill_registry") as mock:
        mock.reload = MagicMock()
        mock.is_registered = MagicMock(return_value=True)
        mock.get_skill = MagicMock(return_value=MagicMock())
        yield mock


@pytest.fixture
def mock_skill_mapping():
    """Mock skill mapping dictionary."""
    with patch("backend.custom_skills.SKILL_MAPPING", {}) as mapping:
        yield mapping


@pytest.fixture
def mock_skill_manager(mock_file_system_auto):
    """Mock skill manager that skips module reloading."""
    from backend.main import api_app
    from backend.routers.api.skill import get_skill_manager

    class MockSkillManager(SkillManager):
        def _reload_and_validate_skill(self, class_name: str, module_name: str) -> None:
            pass  # Skip module reload in tests

    manager = MockSkillManager(SkillConfigStorage(), fs=mock_file_system_auto)
    api_app.dependency_overrides[get_skill_manager] = lambda: manager
    yield manager
    api_app.dependency_overrides.pop(get_skill_manager, None)


@pytest.fixture
def setup_skill_config(mock_firestore_client, skill_config_data):
    """Helper fixture to set up skill config in mock firestore."""

    def _setup(config_data=None, skill_id="skill1"):
        data = config_data or skill_config_data
        mock_firestore_client.setup_mock_data("skill_configs", skill_id, data)
        return data

    return _setup


# Tests with common fixtures
@pytest.mark.usefixtures("mock_get_current_user", "mock_skill_registry")
class TestSkillEndpoints:
    def test_update_skill_config_success(
        self,
        mock_openai_client,  # noqa: ARG002
        mock_skill_module,
        mock_skill_mapping,
        mock_file_system_auto,
        skill_config_data,
        client,
        setup_skill_config,
        mock_skill_manager,
    ):
        mock_skill_mapping["TestSkill"] = mock_skill_module.TestSkill
        setup_skill_config()

        skill_config_data = skill_config_data.copy()
        skill_config_data["title"] = "Skill 1 Updated"
        skill_config_data["content"] = VALID_SKILL_CODE
        response = client.put("/api/skill", json=skill_config_data)
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1
        assert response.json()["data"][0]["id"] == "skill1"

        # Verify if the skill configuration is updated in the mock Firestore client
        updated_config = SkillConfigStorage().load_by_id("skill1")
        assert updated_config.title == "Skill 1 Updated"
        assert updated_config.content == VALID_SKILL_CODE

        # Verify the skill was properly registered
        assert "TestSkill" in mock_skill_mapping
        assert mock_skill_mapping["TestSkill"] == mock_skill_module.TestSkill

        # Verify file operations were performed on the mock file system
        expected_path = mock_skill_manager.skills_dir / "testskill.py"
        assert mock_file_system_auto.files.get(str(expected_path)) == VALID_SKILL_CODE

    def test_get_skill_list(self, client, setup_skill_config):
        setup_skill_config()
        response = client.get("/api/skill/list")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    def test_get_skill_config_success(self, client, skill_config_data, setup_skill_config):
        setup_skill_config()
        response = client.get(f"/api/skill?id={skill_config_data['id']}")
        assert response.status_code == 200
        assert response.json()["data"] == skill_config_data

    def test_get_skill_config_forbidden(self, client, skill_config_data, setup_skill_config):
        modified_data = skill_config_data.copy()
        modified_data["user_id"] = "different_user"
        setup_skill_config(modified_data)

        response = client.get(f"/api/skill?id={skill_config_data['id']}")
        assert response.status_code == 403
        assert response.json() == {"data": {"message": "You don't have permissions to access this skill"}}

    def test_get_skill_config_not_found(self, client):
        skill_id = "nonexistent_skill"
        response = client.get(f"/api/skill?id={skill_id}")
        assert response.status_code == 404
        assert response.json() == {"data": {"message": "Skill not found: nonexistent_skill"}}

    def test_delete_skill_success(self, client, setup_skill_config, mock_firestore_client):
        setup_skill_config()
        response = client.delete("/api/skill?id=skill1")
        assert response.status_code == 200
        assert response.json() == {"status": True, "message": "Skill configuration deleted", "data": []}
        assert mock_firestore_client.to_dict() == {}

    def test_delete_skill_forbidden(self, client, skill_config_data, setup_skill_config):
        modified_data = skill_config_data.copy()
        modified_data["user_id"] = "different_user"
        setup_skill_config(modified_data)

        response = client.delete("/api/skill?id=skill1")
        assert response.status_code == 403
        assert response.json() == {"data": {"message": "You don't have permissions to access this skill"}}

    def test_delete_skill_not_found(self, client):
        skill_id = "nonexistent_skill"
        response = client.delete(f"/api/skill?id={skill_id}")
        assert response.status_code == 404
        assert response.json() == {"data": {"message": "Skill not found: nonexistent_skill"}}

    def test_update_skill_config_user_id_mismatch(self, client, skill_config_data, setup_skill_config):
        modified_data = skill_config_data.copy()
        modified_data["user_id"] = "another_user"
        setup_skill_config(modified_data)

        response = client.put("/api/skill", json=modified_data)
        assert response.status_code == 403
        assert response.json() == {"data": {"message": "You don't have permissions to access this skill"}}

    def test_update_skill_config_not_found(self, client, skill_config_data, setup_skill_config):
        setup_skill_config()
        modified_data = skill_config_data.copy()
        modified_data["id"] = "nonexistent_skill"
        response = client.put("/api/skill", json=modified_data)
        assert response.status_code == 404
        assert response.json() == {"data": {"message": "Skill not found: nonexistent_skill"}}

    @patch("backend.services.skill_executor.SkillExecutor.execute_skill", MagicMock(return_value="Execution result"))
    def test_execute_skill_success(self, client, skill_config_data, setup_skill_config):
        setup_skill_config()

        response = client.post("/api/skill/execute", json={"id": skill_config_data["id"], "user_prompt": "test prompt"})
        assert response.status_code == 200
        assert response.json()["data"] == "Execution result"

    def test_execute_skill_not_found(self, client):
        skill_id = "nonexistent_skill"
        response = client.post("/api/skill/execute", json={"id": skill_id, "user_prompt": "test prompt"})
        assert response.status_code == 404
        assert response.json() == {"data": {"message": "Skill not found: nonexistent_skill"}}
