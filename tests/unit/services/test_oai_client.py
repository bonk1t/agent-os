from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.exceptions import UnsetVariableError


@pytest.fixture
def mock_openai_client(recover_oai_client):  # noqa: ARG001
    with patch("backend.services.oai_client.openai.OpenAI") as mock:
        yield mock


@pytest.fixture
def mock_azure_openai_client(recover_oai_client):  # noqa: ARG001
    with patch("backend.services.oai_client.openai.AzureOpenAI") as mock:
        yield mock


def test_get_openai_client_uses_correct_api_key(mock_openai_client):
    # Setup
    from backend.services.oai_client import get_openai_client

    expected_api_key = "test_api_key"
    mock_user_variable_manager = MagicMock()
    mock_user_variable_manager.get_by_key.side_effect = [
        UnsetVariableError("AZURE_OPENAI_API_KEY"),
        expected_api_key,
    ]

    # Execute
    client = get_openai_client(user_variable_manager=mock_user_variable_manager)

    # Verify
    mock_user_variable_manager.get_by_key.assert_any_call("AZURE_OPENAI_API_KEY")
    mock_user_variable_manager.get_by_key.assert_any_call("OPENAI_API_KEY")
    mock_openai_client.assert_called_with(
        api_key=expected_api_key,
        timeout=httpx.Timeout(60.0, read=30, connect=5.0),
        max_retries=5,
        default_headers={"OpenAI-Beta": "assistants=v2"},
    )
    assert client == mock_openai_client.return_value


def test_get_openai_client_uses_azure_openai_when_keys_are_set(mock_azure_openai_client):
    # Setup
    from backend.services.oai_client import get_openai_client

    expected_azure_api_key = "test_azure_api_key"
    expected_api_version = "test_api_version"
    expected_azure_endpoint = "test_azure_endpoint"
    mock_user_variable_manager = MagicMock()
    mock_user_variable_manager.get_by_key.side_effect = [
        expected_azure_api_key,
        expected_api_version,
        expected_azure_endpoint,
    ]

    # Execute
    client = get_openai_client(user_variable_manager=mock_user_variable_manager)

    # Verify
    mock_user_variable_manager.get_by_key.assert_any_call("AZURE_OPENAI_API_KEY")
    mock_user_variable_manager.get_by_key.assert_any_call("OPENAI_API_VERSION")
    mock_user_variable_manager.get_by_key.assert_any_call("AZURE_OPENAI_ENDPOINT")
    mock_azure_openai_client.assert_called_with(
        api_key=expected_azure_api_key,
        api_version=expected_api_version,
        azure_endpoint=expected_azure_endpoint,
        timeout=httpx.Timeout(60.0, read=30, connect=5.0),
        max_retries=5,
    )
    assert client == mock_azure_openai_client.return_value


def test_get_openai_client_falls_back_to_openai_when_azure_keys_are_not_set(mock_openai_client):
    # Setup
    from backend.services.oai_client import get_openai_client

    expected_api_key = "test_api_key"
    mock_user_variable_manager = MagicMock()
    mock_user_variable_manager.get_by_key.side_effect = [
        UnsetVariableError("AZURE_OPENAI_API_KEY"),
        expected_api_key,
    ]

    # Execute
    client = get_openai_client(user_variable_manager=mock_user_variable_manager)

    # Verify
    mock_user_variable_manager.get_by_key.assert_any_call("AZURE_OPENAI_API_KEY")
    mock_user_variable_manager.get_by_key.assert_any_call("OPENAI_API_KEY")
    mock_openai_client.assert_called_with(
        api_key=expected_api_key,
        timeout=httpx.Timeout(60.0, read=30, connect=5.0),
        max_retries=5,
        default_headers={"OpenAI-Beta": "assistants=v2"},
    )
    assert client == mock_openai_client.return_value


@pytest.mark.usefixtures("recover_oai_client")
def test_get_openai_client_raises_error_when_no_api_key_and_user_variable_manager():
    from backend.services.oai_client import get_openai_client

    # Execute
    with pytest.raises(ValueError) as e:
        get_openai_client()

    # Verify
    assert str(e.value) == "Either user_variable_manager or api_key must be provided"


@pytest.mark.usefixtures("recover_oai_client")
def test_get_openai_client_raises_error_when_no_valid_api_key_in_user_variables():
    # Setup
    from backend.services.oai_client import get_openai_client

    mock_user_variable_manager = MagicMock()
    mock_user_variable_manager.get_by_key.side_effect = UnsetVariableError("OPENAI_API_KEY")

    # Execute
    with pytest.raises(ValueError) as e:
        get_openai_client(user_variable_manager=mock_user_variable_manager)

    # Verify
    assert str(e.value) == "API key not provided and no valid API key found in user variables"
