from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import AuthenticationError as OpenAIAuthenticationError
from pydantic import ValidationError

from backend.dependencies.dependencies import get_agency_adapter
from backend.exceptions import UnsetVariableError
from backend.models.agency_config import AgencyConfig
from backend.repositories.agency_config_storage import AgencyConfigStorage
from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.services.agency_manager import AgencyManager


@pytest.fixture
def mock_agency_adapter_to_raise_pydantic_validation_error():
    from backend.main import api_app

    def raise_error():
        raise ValidationError.from_exception_data("Validation Error", line_errors=[])

    api_app.dependency_overrides[get_agency_adapter] = raise_error
    yield
    api_app.dependency_overrides[get_agency_adapter] = get_agency_adapter


@pytest.fixture
def mock_agent_storage_to_raise_openai_authentication_error():
    request = httpx.Request(method="GET", url="http://testserver/api/agent?id=123")
    response = httpx.Response(401, request=request)
    exception = OpenAIAuthenticationError("Authentication Error", response=response, body={})
    with patch.object(AgentFlowSpecStorage, "load_by_id", side_effect=exception):
        yield


@pytest.fixture
def mock_agent_storage_to_raise_unhandled_exception():
    with patch.object(AgencyConfigStorage, "load_by_id", side_effect=Exception("Unhandled Exception")):
        yield


@pytest.mark.usefixtures("mock_get_current_user", "mock_agency_adapter_to_raise_pydantic_validation_error")
def test_pydantic_validation_error(caplog, client, agency_adapter, mock_firestore_client, agent_config_data_db):
    caplog.set_level(10)

    agency_data_db = {
        "id": "existing_agency",
        "name": "Existing Agency",
        "shared_instructions": "Existing",
        "main_agent": "Sender Agent",
        "agents": ["sender_agent_id"],
        "flows": [],
    }
    mock_firestore_client.setup_mock_data("agency_configs", "existing_agency", agency_data_db)
    mock_firestore_client.setup_mock_data("agent_configs", "sender_agent_id", agent_config_data_db)
    agency_data_api = agency_adapter.to_api(AgencyConfig(**agency_data_db)).model_dump()

    response = client.put("/api/agency", json=agency_data_api)

    assert response.status_code == 400
    assert "message" in response.json()["data"]
    assert response.json()["data"]["message"] == "Invalid request"
    assert response.json()["data"]["errors"] == []
    assert "Validation Error" in caplog.text


@pytest.mark.usefixtures("mock_get_current_user")
def test_request_validation_error(client):
    template_config = {
        "id": "template_agency_id",
        "name": "Test agency",
        "shared_instructions": "Manifesto",
        "flows": [{"sender": None, "receiver": None}],
    }

    response = client.put("/api/agency", json=template_config)
    assert response.status_code == 422
    assert "message" in response.json()["data"]
    assert response.json()["data"]["message"] == "Sender agent is required"
    assert response.json()["data"]["errors"] == [
        {
            "ctx": {"error": {}},
            "input": None,
            "loc": ["body", "flows", 0, "sender"],
            "msg": "Value error, Sender agent is required",
            "type": "value_error",
        }
    ]


@pytest.mark.usefixtures("mock_get_current_user")
def test_http_exception(client, mock_firestore_client, agent_config_data_db):
    agent_config_data_db["user_id"] = "another_user_id"
    mock_firestore_client.setup_mock_data("agent_configs", "123", agent_config_data_db)

    # Mock the agent manager to raise an HTTPException
    from http import HTTPStatus

    from fastapi import HTTPException

    from backend.routers.api.agent import get_agent_manager

    def mock_get_agent_manager():
        manager = MagicMock()
        manager.get_agent.side_effect = HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail="You don't have permissions to access this agent"
        )
        return manager

    from backend.main import api_app

    api_app.dependency_overrides[get_agent_manager] = mock_get_agent_manager

    try:
        response = client.get("/api/agent?id=123")
        assert response.status_code == 403
        assert "message" in response.json()["data"]
        assert response.json()["data"]["message"] == "You don't have permissions to access this agent"
    finally:
        api_app.dependency_overrides.pop(get_agent_manager, None)


@pytest.mark.usefixtures("mock_get_current_user")
def test_not_found_error(client):
    response = client.get("/api/agent?id=123")
    assert response.status_code == 404
    assert "message" in response.json()["data"]
    assert "Agent not found: 123" in response.json()["data"]["message"]


@pytest.mark.usefixtures("mock_get_current_user", "mock_agent_storage_to_raise_openai_authentication_error")
def test_openai_authentication_error(client, caplog):
    caplog.set_level("WARNING")
    response = client.get("/api/agent?id=123")
    assert response.status_code == 401
    assert "message" in response.json()["data"]
    assert "Authentication Error" in response.json()["data"]["message"]
    assert "request: http://testserver/api/agent?id=123 exc: Authentication Error" in caplog.text


@pytest.mark.usefixtures("mock_get_current_user")
def test_unset_variable_error(client):
    with patch.object(AgencyManager, "get_agency", side_effect=UnsetVariableError(key="MISSING_KEY")):
        response = client.post("/api/session?agency_id=123")
    assert response.status_code == 400
    assert "message" in response.json()["data"]
    assert "Variable MISSING_KEY is not set. Please set it first." in response.json()["data"]["message"]


@pytest.mark.usefixtures("mock_get_current_user", "mock_agent_storage_to_raise_unhandled_exception")
def test_unhandled_exception(client, caplog):
    caplog.set_level("ERROR")

    client.get("/api/agency?id=123")

    assert "Unhandled Exception" in caplog.text
    assert "request: http://testserver/api/agency?id=123" in caplog.text
