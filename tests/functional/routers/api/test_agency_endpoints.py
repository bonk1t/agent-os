from copy import deepcopy
from unittest import mock
from unittest.mock import AsyncMock, patch

import pytest

from backend.models.agency_config import AgencyConfig, AgencyConfigForAPI
from backend.models.agent_flow_spec import AgentFlowSpec
from tests.testing_utils import TEST_USER_ID
from tests.testing_utils.constants import TEST_AGENCY_ID


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agency_list_success(client, mock_firestore_client, agency_adapter):
    # Setup expected response
    db_agency = AgencyConfig(
        id="agency1",
        user_id=TEST_USER_ID,
        name="Test agency",
        main_agent="Sender Agent",
        agents=["sender_agent_id", "receiver_agent_id"],
        agency_chart={"0": ["Sender Agent", "Receiver Agent"]},
        timestamp="2024-05-05T00:14:57.487901+00:00",
    )
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, db_agency.model_dump())
    mock_firestore_client.setup_mock_data(
        "agent_configs",
        "sender_agent_id",
        {"id": "sender_agent_id", "config": {"name": "Sender Agent"}, "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    mock_firestore_client.setup_mock_data(
        "agent_configs",
        "receiver_agent_id",
        {
            "id": "receiver_agent_id",
            "config": {"name": "Receiver Agent"},
            "timestamp": "2024-05-05T00:14:57.487901+00:00",
        },
    )
    expected_agency = agency_adapter.to_api(db_agency)

    response = client.get("/api/agency/list")

    assert response.status_code == 200
    assert response.json()["data"] == [expected_agency.model_dump()]


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agency_config(client, mock_firestore_client, agency_adapter):
    db_agency = AgencyConfig(
        id=TEST_AGENCY_ID,
        user_id=TEST_USER_ID,
        name="Test agency",
        description="Test Description",
        shared_instructions="Test Manifesto",
        main_agent="Sender Agent",
        agents=["sender_agent_id"],
        timestamp="2024-05-05T00:14:57.487901+00:00",
    )
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, db_agency)
    mock_firestore_client.setup_mock_data(
        "agent_configs",
        "sender_agent_id",
        {"id": "sender_agent_id", "config": {"name": "Sender Agent"}, "timestamp": "2024-05-05T00:14:57.487901+00:00"},
    )
    expected_agency = agency_adapter.to_api(db_agency)

    response = client.get("/api/agency?id=test_agency_id")
    assert response.status_code == 200
    assert response.json()["data"] == expected_agency.model_dump()


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agency_config_not_found(client):
    # Simulate non-existent agency by not setting up any data for it
    response = client.get("/api/agency?id=non_existent_agency")
    assert response.status_code == 404
    assert response.json() == {"data": {"message": "Agency not found: non_existent_agency"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_agency_config_user_id_mismatch(client, mock_firestore_client):
    expected_agency = AgencyConfig(
        id="agency1",
        user_id="different_user_id",
        name="Test agency",
        agents=["sender_agent_id"],
        main_agent="Sender Agent",
    )
    mock_firestore_client.setup_mock_data("agency_configs", "agency1", expected_agency.model_dump())

    response = client.get("/api/agency?id=agency1")
    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to access this agency"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_create_agency_success(
    client, agent_config_data_api, agent_config_data_db, agency_adapter, mock_firestore_client
):
    template_config = {
        "id": "template_agency_id",
        "name": "Test agency",
        "shared_instructions": "Manifesto",
        "flows": [{"sender": agent_config_data_api, "receiver": None}],
    }
    mock_firestore_client.setup_mock_data("agent_configs", "sender_agent_id", agent_config_data_db)

    with patch(
        "backend.services.agency_manager.AgencyManager.handle_agency_creation_or_update", new_callable=AsyncMock
    ) as mock_create_or_update_agency:
        mock_create_or_update_agency.return_value = TEST_AGENCY_ID
        response = client.put("/api/agency", json=template_config)

    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)
    expected_config = agency_adapter.to_model(AgencyConfigForAPI(**template_config))
    expected_config.timestamp = mock.ANY
    mock_create_or_update_agency.assert_called_once_with(expected_config, TEST_USER_ID)


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agency_success(
    client, mock_firestore_client, agent_config_data_api, agent_config_data_db, agency_adapter
):
    # Setup initial data in mock Firestore client
    initial_db_data = {
        "id": TEST_AGENCY_ID,
        "user_id": TEST_USER_ID,
        "name": "Test agency",
        "description": "Test Description",
        "shared_instructions": "Original Manifesto",
        "agents": ["sender_agent_id"],
        "main_agent": "Sender Agent",
        "timestamp": "2024-05-05T00:14:57.487901+00:00",
    }
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, initial_db_data)
    mock_firestore_client.setup_mock_data("agent_configs", "sender_agent_id", agent_config_data_db)
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
    new_data_payload = {
        "id": TEST_AGENCY_ID,
        "name": "Test agency",
        "description": "Test Description",
        "shared_instructions": "Updated Manifesto",
        "flows": [{"sender": agent_config_data_api, "receiver": None}],
        "user_id": TEST_USER_ID,
    }
    expected_data_from_api = new_data_payload.copy()
    expected_data_from_api["timestamp"] = mock.ANY

    response = client.put("/api/agency", json=new_data_payload)

    assert response.status_code == 200
    assert response.json()["data"] == [expected_data_from_api]
    expected_data = agency_adapter.to_model(AgencyConfigForAPI(**new_data_payload)).model_dump()
    expected_data["timestamp"] = mock.ANY
    assert mock_firestore_client.collection("agency_configs").to_dict() == expected_data


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agency_user_id_mismatch(client, mock_firestore_client, agent_config_data_api):
    # Setup initial data in mock Firestore client
    initial_data = {
        "id": TEST_AGENCY_ID,
        "user_id": "some_other_user",
        "name": "Test agency",
        "main_agent": "Sender Agent",
    }
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, initial_data)
    new_data = initial_data.copy()
    new_data.update(
        {"shared_instructions": "Updated Manifesto", "flows": [{"sender": agent_config_data_api, "receiver": None}]}
    )

    response = client.put("/api/agency", json=new_data)

    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to access this agency"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_update_agency_with_foreign_agent(client, mock_firestore_client, agency_adapter):
    db_agency = {
        "id": TEST_AGENCY_ID,
        "user_id": TEST_USER_ID,
        "name": "Test Agency",
        "agents": ["sender_agent_id", "foreign_agent_id"],
        "main_agent": "Sender Agent",
    }
    foreign_agent_flow_spec = AgentFlowSpec(
        config={"name": "Foreign Agent"},
        user_id="foreign_user_id",
    )
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, db_agency)
    mock_firestore_client.setup_mock_data(
        "agent_configs", "sender_agent_id", {"id": "sender_agent_id", "config": {"name": "Sender Agent"}}
    )
    mock_firestore_client.setup_mock_data("agent_configs", "foreign_agent_id", foreign_agent_flow_spec.model_dump())
    # Simulate a PUT request to update the agency with agents belonging to a different user
    new_data = agency_adapter.to_api(AgencyConfig(**db_agency)).model_dump()
    response = client.put("/api/agency", json=new_data)
    # Check if the server responds with a 403 Forbidden
    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to use agent sender_agent_id"}}
    # Check if the agency config was not updated
    assert mock_firestore_client.collection("agency_configs").to_dict() == db_agency


@pytest.mark.usefixtures("mock_get_current_user")
def test_create_or_update_agency_missing_agent(client, agency_adapter, mock_firestore_client, agent_config_data_db):
    missing_agent_db = deepcopy(agent_config_data_db)
    missing_agent_db["id"] = "missing_agent_id"
    missing_agent_db["config"]["name"] = "Missing Agent"
    agency_data_with_missing_agent_db = {
        "id": "existing_agency",
        "name": "Existing Agency with Missing Agent",
        "shared_instructions": "Existing",
        "main_agent": "Sender Agent",
        "agents": ["sender_agent_id", "missing_agent_id"],
        "agency_chart": {"0": ["Sender Agent", "Missing Agent"]},
        "flows": [{"sender": missing_agent_db, "receiver": None}],
    }
    mock_firestore_client.setup_mock_data("agent_configs", "sender_agent_id", agent_config_data_db)
    mock_firestore_client.setup_mock_data("agent_configs", "missing_agent_id", missing_agent_db)  # only for adapter
    agency_data_with_missing_agent_api = agency_adapter.to_api(
        AgencyConfig(**agency_data_with_missing_agent_db)
    ).model_dump()
    mock_firestore_client.collection("agent_configs").document("missing_agent_id").delete()  # remove it

    mock_firestore_client.setup_mock_data("agency_configs", "existing_agency", agency_data_with_missing_agent_db)
    response = client.put("/api/agency", json=agency_data_with_missing_agent_api)
    assert response.status_code == 400
    assert response.json() == {"data": {"message": "Agent not found: missing_agent_id"}}


@pytest.mark.usefixtures("mock_get_current_user", "mock_session_storage")
@patch("backend.services.session_manager.get_openai_client")
def test_delete_agency_success(mock_openai_client, client, mock_firestore_client, session_config_data):
    db_agency = {"id": TEST_AGENCY_ID, "user_id": TEST_USER_ID, "name": "Test Agency", "main_agent": "sender_agent_id"}
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, db_agency)
    mock_firestore_client.setup_mock_data("session_configs", "test_session_id", session_config_data)

    response = client.delete(f"/api/agency?id={TEST_AGENCY_ID}")
    assert response.status_code == 200
    assert response.json() == {"status": True, "message": "Agency deleted", "data": []}
    assert mock_firestore_client.collection("agency_configs").to_dict() == {}
    assert mock_firestore_client.collection("session_configs").to_dict() == {}
    mock_openai_client.return_value.beta.threads.delete.assert_called_with(thread_id="test_session_id", timeout=30.0)


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_agency_not_found(client):
    response = client.delete("/api/agency?id=non_existent_agency")
    assert response.status_code == 404
    assert response.json() == {"data": {"message": "Agency not found: non_existent_agency"}}


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_agency_user_id_mismatch(client, mock_firestore_client):
    db_agency = {
        "id": TEST_AGENCY_ID,
        "user_id": "some_other_user",
        "name": "Test Agency",
        "main_agent": "sender_agent_id",
    }
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, db_agency)

    response = client.delete(f"/api/agency?id={TEST_AGENCY_ID}")
    assert response.status_code == 403
    assert response.json() == {"data": {"message": "You don't have permissions to access this agency"}}
