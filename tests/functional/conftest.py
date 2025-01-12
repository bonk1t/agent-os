from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.dependencies.auth import get_current_user
from backend.models.skill_config import SkillConfig
from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.services.adapters.agency_adapter import AgencyAdapter
from backend.services.adapters.agent_adapter import AgentAdapter
from tests.testing_utils import TEST_USER_ID, get_current_superuser_override, get_current_user_override
from tests.testing_utils.constants import TEST_AGENT_ID


@pytest.mark.usefixtures("mock_setup_logging")
@pytest.fixture
def mock_get_current_user():
    from backend.main import api_app

    api_app.dependency_overrides[get_current_user] = get_current_user_override
    yield
    api_app.dependency_overrides[get_current_user] = get_current_user


@pytest.mark.usefixtures("mock_setup_logging")
@pytest.fixture
def mock_get_current_superuser():
    from backend.main import api_app

    api_app.dependency_overrides[get_current_user] = get_current_superuser_override
    yield
    api_app.dependency_overrides[get_current_user] = get_current_user


@pytest.mark.usefixtures("mock_setup_logging")
@pytest.fixture
def client():
    from backend.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_session_storage(mock_firestore_client, session_config_data):
    mock_firestore_client.setup_mock_data("session_configs", "test_session_id", session_config_data)


@pytest.fixture
@pytest.mark.usefixtures("mock_firestore_client")
def agency_adapter():
    return AgencyAdapter(AgentFlowSpecStorage(), AgentAdapter(SkillConfigStorage()))


@pytest.fixture
def agent_config_data_api():
    return {
        "id": TEST_AGENT_ID,
        "config": {
            "name": "Sender Agent",
            "system_message": "Do something important.",
            "model": "gpt-4o",
            "code_execution_config": {
                "work_dir": None,
                "use_docker": False,
            },
            "temperature": 0.0,
        },
        "timestamp": "2024-05-05T00:14:57.487901+00:00",
        "skills": [
            SkillConfig(title="GenerateProposal", timestamp="2024-05-05T00:14:57.487901+00:00").model_dump(),
            SkillConfig(title="SearchWeb", timestamp="2024-05-05T00:14:57.487901+00:00").model_dump(),
        ],
        "description": "An example agent.",
        "user_id": TEST_USER_ID,
        "temperature": 0.0,
    }


@pytest.fixture
def agent_config_data_db(agent_config_data_api):
    db_config = agent_config_data_api.copy()
    db_config["skills"] = ["GenerateProposal", "SearchWeb"]
    return db_config


@pytest.fixture(autouse=True)
def mock_file_system_auto():
    """Automatically mock file system for all tests."""

    class MockFileSystem:
        def __init__(self):
            self.files = {}

        def write_file(self, path: Path, content: str) -> None:
            self.files[str(path)] = content

        def remove_file(self, path: Path) -> None:
            self.files.pop(str(path), None)

        def file_exists(self, path: Path) -> bool:
            return str(path) in self.files

    mock_fs = MockFileSystem()
    with patch("backend.services.skill_manager.RealFileSystem", return_value=mock_fs):
        yield mock_fs
