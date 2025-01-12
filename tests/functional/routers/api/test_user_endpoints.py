import pytest

from backend.services.encryption_service import EncryptionService
from backend.settings import settings
from tests.testing_utils import TEST_USER_ID


@pytest.fixture
def agent_data():
    return {
        "id": "agent1",
        "config": {
            "name": "example_name",
            "system_message": "Do something important",
            "code_execution_config": {
                "work_dir": "test_agency_dir",
                "use_docker": False,
            },
        },
        "timestamp": "2024-04-04T09:39:13.048457+00:00",
        "skills": ["skill1", "skill2"],
        "description": "An example agent",
        "user_id": TEST_USER_ID,
    }


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_variables(client, mock_firestore_client):
    mock_firestore_client.setup_mock_data(
        "user_variables", TEST_USER_ID, {"VARIABLE1": "value1", "VARIABLE2": "value2"}
    )
    response = client.get("/api/user/settings/variables")
    assert response.status_code == 200
    assert response.json()["data"] == ["OPENAI_API_KEY", "VARIABLE1", "VARIABLE2"]


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_variables(client, mock_firestore_client):
    variables = {"VARIABLE1": "value1", "VARIABLE2": "value2"}
    response = client.put("/api/user/settings/variables", json=variables)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Variables updated successfully",
        "status": True,
        "data": ["OPENAI_API_KEY", "VARIABLE1", "VARIABLE2"],
    }
    updated_variables = mock_firestore_client.to_dict()
    assert len(updated_variables) == 2


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_open_ai_key_variable_fail(client, mock_firestore_client, agent_data):
    mock_firestore_client.setup_mock_data("agent_configs", "agent1", agent_data)
    mock_firestore_client.setup_mock_data(
        "user_variables", TEST_USER_ID, {"OPENAI_API_KEY": EncryptionService(settings.encryption_key).encrypt("value1")}
    )
    variables = {"OPENAI_API_KEY": "value2"}
    response = client.put("/api/user/settings/variables", json=variables)
    assert response.status_code == 200
    assert response.json() == {
        "message": "Please delete all agents and teams to update the Open AI API key",
        "status": False,
        "data": ["OPENAI_API_KEY"],
    }
    updated_variables = mock_firestore_client.to_dict()
    assert len(updated_variables) == 1
