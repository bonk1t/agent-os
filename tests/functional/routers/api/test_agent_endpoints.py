from unittest import mock
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.models.skill_config import SkillConfig
from tests.testing_utils.constants import TEST_AGENCY_ID, TEST_AGENT_ID, TEST_USER_ID


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agent_list(agent_config_data_api, agent_config_data_db, client, mock_firestore_client):
    # define a template agent configuration
    mock_agent_data_db_template = agent_config_data_db.copy()
    mock_agent_data_db_template["id"] = "agent2"
    mock_agent_data_db_template["user_id"] = None

    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data("agent_configs", "agent2", mock_agent_data_db_template)
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "GenerateProposal",
        {"title": "GenerateProposal", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "SearchWeb",
        {"title": "SearchWeb", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )

    response = client.get("/api/agent/list")
    assert response.status_code == 200
    assert response.json()["data"] == [agent_config_data_api]


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agent_list_owned_by_user(agent_config_data_api, agent_config_data_db, client, mock_firestore_client):
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "GenerateProposal",
        {"title": "GenerateProposal", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "SearchWeb",
        {"title": "SearchWeb", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )

    response = client.get("/api/agent/list?owned_by_user=true")
    assert response.status_code == 200
    assert response.json()["data"] == [agent_config_data_api]


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agent_config(client, agent_config_data_api, agent_config_data_db, mock_firestore_client):
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "GenerateProposal",
        {"title": "GenerateProposal", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "SearchWeb",
        {"title": "SearchWeb", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )

    response = client.get(f"/api/agent?id={TEST_AGENT_ID}")
    assert response.status_code == 200
    assert response.json()["data"] == agent_config_data_api


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agent_success(client, agent_config_data_api, agent_config_data_db, mock_firestore_client):
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "GenerateProposal",
        {"title": "GenerateProposal", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "SearchWeb",
        {"title": "SearchWeb", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    expected_data = agent_config_data_api.copy()
    expected_data["config"]["name"] = "Sender Agent (test_user_id)"
    expected_data["timestamp"] = mock.ANY

    response = client.put("/api/agent", json=agent_config_data_api)

    assert response.status_code == 200
    assert response.json()["data"] == [expected_data]


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agent_user_id_mismatch(client, agent_config_data_api, agent_config_data_db, mock_firestore_client):
    agent_data_db = agent_config_data_db.copy()
    agent_data_db["user_id"] = "other_user"
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_data_db)

    response = client.put("/api/agent", json=agent_config_data_api)

    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to access this agent"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_create_agent_from_template(client, agent_config_data_api, mock_firestore_client, caplog):
    caplog.set_level("INFO")
    mock_firestore_client.setup_mock_data("skill_configs", "GenerateProposal", {"title": "GenerateProposal"})
    mock_firestore_client.setup_mock_data("skill_configs", "SearchWeb", {"title": "SearchWeb"})
    agent_config_data_api["user_id"] = None

    with patch("backend.services.agent_manager.AgentManager._construct_agent") as mock_construct_agent:
        mock_construct_agent.return_value = Mock(id=TEST_AGENT_ID)

        response = client.put("/api/agent", json=agent_config_data_api)

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == TEST_AGENT_ID
    assert response.json()["data"][0]["config"]["name"] == "Sender Agent (test_user_id)"
    assert "Creating agent for user: test_user_id, agent: Sender Agent" in caplog.text


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agent_invalid_skill(client, agent_config_data_api, agent_config_data_db, mock_firestore_client):
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data(
        "skill_configs",
        "SearchWeb",
        {"title": "SearchWeb", "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    agent_config_data_api["skills"] = [
        SkillConfig(title="NonExistentSkill").model_dump(),
        SkillConfig(title="SearchWeb").model_dump(),
    ]

    with patch("backend.services.agent_manager.AgentManager") as mock_agent_manager:
        mock_agent_manager.return_value = AsyncMock()
        mock_agent_manager.return_value.create_or_update_agent.return_value = TEST_AGENT_ID

        response = client.put("/api/agent", json=agent_config_data_api)

    assert response.status_code == 400
    assert response.json() == {"data": {"message": "Some skills are not supported: {'NonExistentSkill'}"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_agent_success(client, agent_config_data_db, mock_firestore_client):
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)

    with patch("backend.services.agent_manager.AgentManager") as mock_agent_manager:
        mock_agent_manager.return_value = AsyncMock()
        mock_agent_manager.return_value.delete_agent.return_value = TEST_AGENT_ID

        response = client.delete(f"/api/agent?id={TEST_AGENT_ID}")

    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["message"] == "Agent configuration deleted"


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_agent_user_id_mismatch(client, agent_config_data_db, mock_firestore_client):
    agent_data_db = agent_config_data_db.copy()
    agent_data_db["user_id"] = "other_user"
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_data_db)

    response = client.delete(f"/api/agent?id={TEST_AGENT_ID}")

    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to access this agent"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_agent_used_in_agencies(client, agent_config_data_db, mock_firestore_client):
    agency_data = {
        "user_id": TEST_USER_ID,
        "id": TEST_AGENCY_ID,
        "name": "Test Agency",
        "main_agent": "sender_agent_id",
        "agents": [TEST_AGENT_ID],
    }
    mock_firestore_client.setup_mock_data("agent_configs", TEST_AGENT_ID, agent_config_data_db)
    mock_firestore_client.setup_mock_data("agency_configs", "test_agency_id", agency_data)

    response = client.delete(f"/api/agent?id={TEST_AGENT_ID}")

    assert response.status_code == 400
    assert response.json() == {
        "data": {"message": "Agent cannot be deleted as it is currently used in a team configuration"}
    }
