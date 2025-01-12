from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.exceptions import NotFoundError
from backend.services.agency_manager import AgencyManager
from tests.testing_utils import TEST_USER_ID
from tests.testing_utils.constants import TEST_AGENCY_ID


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_session_list(session_config_data, client, mock_firestore_client):
    mock_firestore_client.setup_mock_data("session_configs", "test_session_id", session_config_data)
    agency_config = {"name": "Test agency", "id": TEST_AGENCY_ID, "main_agent": "sender_agent_id"}
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, agency_config)
    expected_session_data = session_config_data.copy()
    expected_session_data["flow_config"] = mock.ANY

    response = client.get("/api/session/list")
    assert response.status_code == 200
    assert response.json()["data"] == [expected_session_data]


@pytest.mark.usefixtures("mock_get_current_user")
def test_create_session_success(client, mock_firestore_client):
    agency_mock = MagicMock()
    agency_mock.main_thread.id = "new_session_id"
    agency_config_mock = MagicMock()
    agency_config_mock.name = "Test agency"
    with patch.object(
        AgencyManager, "get_agency", AsyncMock(return_value=(agency_mock, agency_config_mock))
    ) as mock_get_agency:
        # mock Firestore to pass the security user_id check
        agency_config = {
            "id": TEST_AGENCY_ID,
            "name": "Test agency",
            "user_id": TEST_USER_ID,
            "main_agent": "sender_agent_id",
        }
        mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, agency_config)

        response = client.post(f"/api/session?agency_id={TEST_AGENCY_ID}")
        # Assertions
        assert response.status_code == 200
        assert response.json()["data"] == [
            {
                "agency_id": TEST_AGENCY_ID,
                "id": "new_session_id",
                "name": "Test agency",
                "thread_ids": mock.ANY,
                "timestamp": mock.ANY,
                "user_id": TEST_USER_ID,
                "flow_config": mock.ANY,
            }
        ]
        mock_get_agency.assert_awaited_once_with(TEST_AGENCY_ID, thread_ids={}, user_id=TEST_USER_ID)

        # Check if the session config was created
        assert mock_firestore_client.collection("session_configs").to_dict() == {
            "id": "new_session_id",
            "name": "Test agency",
            "user_id": TEST_USER_ID,
            "agency_id": TEST_AGENCY_ID,
            "thread_ids": {},
            "timestamp": mock.ANY,
        }


@pytest.mark.usefixtures("mock_get_current_user")
def test_create_session_agency_not_found(client, mock_firestore_client):
    with patch.object(
        AgencyManager, "get_agency", AsyncMock(side_effect=NotFoundError("Agency", TEST_AGENCY_ID))
    ) as mock_get_agency:
        response = client.post("/api/session?agency_id=test_session_id")
        assert response.status_code == 404
        assert response.json() == {"data": {"message": "Agency not found: test_agency_id"}}
        assert mock_firestore_client.collection("session_configs").to_dict() == {}
        mock_get_agency.assert_awaited_once_with("test_session_id", thread_ids={}, user_id=TEST_USER_ID)


@pytest.mark.usefixtures("mock_get_current_user")
def test_rename_session_success(
    client, mock_firestore_client, agency_config_data, agent_config_data_db, session_config_data
):
    mock_firestore_client.setup_mock_data("agency_configs", TEST_AGENCY_ID, agency_config_data)
    mock_firestore_client.setup_mock_data("agent_configs", "sender_agent_id", agent_config_data_db)
    mock_firestore_client.setup_mock_data("session_configs", "test_session_id", session_config_data)
    expected_response = session_config_data.copy()
    expected_response["name"] = "New session name"
    expected_response["flow_config"] = mock.ANY

    response = client.post("/api/session/rename", json={"id": "test_session_id", "name": "New session name"})
    assert response.status_code == 200
    assert response.json()["data"] == [expected_response]
    # Check if the session config was updated
    assert mock_firestore_client.collection("session_configs").to_dict() == {
        "id": "test_session_id",
        "name": "New session name",
        "user_id": TEST_USER_ID,
        "agency_id": TEST_AGENCY_ID,
        "thread_ids": {"main_thread": "test_session_id"},
        "timestamp": mock.ANY,
    }


@pytest.mark.usefixtures("mock_get_current_user")
def test_rename_session_not_found(client, mock_firestore_client):
    response = client.post("/api/session/rename", json={"id": "test_session_id", "name": "New session name"})
    assert response.status_code == 404
    assert response.json() == {"data": {"message": "Session not found: test_session_id"}}
    assert mock_firestore_client.collection("session_configs").to_dict() == {}


@pytest.mark.usefixtures("mock_get_current_user")
def test_delete_session_success(client, mock_firestore_client, session_config_data):
    mock_firestore_client.setup_mock_data("session_configs", "test_session_id", session_config_data)

    response = client.delete("/api/session?id=test_session_id")
    assert response.status_code == 200
    assert response.json()["data"] == []
    # Check if the session config was deleted
    assert mock_firestore_client.collection("session_configs").to_dict() == {}
