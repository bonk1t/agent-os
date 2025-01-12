from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import AuthenticationError as OpenAIAuthenticationError
from starlette.websockets import WebSocket

from backend.exceptions import UnsetVariableError
from backend.models.auth import User
from backend.models.message import Message
from backend.models.session_config import SessionConfig


@pytest.mark.asyncio
async def test_handle_websocket_messages(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"

    with patch.object(websocket_handler, "_process_messages", new_callable=AsyncMock) as process_messages_mock:
        process_messages_mock.side_effect = [True, True, False]
        await websocket_handler._handle_websocket_messages(websocket, client_id)

    assert process_messages_mock.await_count == 3
    process_messages_mock.assert_awaited_with(websocket, client_id)


@pytest.mark.asyncio
async def test_process_messages_unset_variable_error(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"
    expected_error_message = "Variable XXX is not set. Please set it first."

    with patch.object(
        websocket_handler, "_process_single_message", new_callable=AsyncMock
    ) as process_single_message_mock:
        process_single_message_mock.side_effect = UnsetVariableError("XXX")
        result = await websocket_handler._process_messages(websocket, client_id)

    assert result is False
    process_single_message_mock.assert_awaited_once_with(websocket, client_id)
    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {"status": False, "message": expected_error_message}, client_id
    )


@pytest.mark.asyncio
async def test_process_messages_openai_authentication_error(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"
    expected_error_message = "Authentication Error"
    request = httpx.Request(method="GET", url="http://testserver/api/agent?id=123")
    response = httpx.Response(401, request=request)

    with patch.object(
        websocket_handler, "_process_single_message", new_callable=AsyncMock
    ) as process_single_message_mock:
        process_single_message_mock.side_effect = OpenAIAuthenticationError(
            expected_error_message, response=response, body={}
        )
        result = await websocket_handler._process_messages(websocket, client_id)

    assert result is False
    process_single_message_mock.assert_awaited_once_with(websocket, client_id)
    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {"status": False, "message": expected_error_message}, client_id
    )


@pytest.mark.asyncio
async def test_process_single_message_user_message(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"
    user_message = "User message"
    session_id = "session_id"
    token = "valid_token"
    user = User(id="user_id", email="user@example.com")
    session = SessionConfig(
        id="session_id",
        name="Session",
        user_id=user.id,
        agency_id="agency_id",
        thread_ids={"thread1": "thread1", "thread2": "thread2"},
    )
    agency = MagicMock()
    all_messages = [
        Message(content="Message 1", session_id=session_id),
        Message(content="Message 2", session_id=session_id),
    ]

    websocket.receive_json.return_value = {
        "type": "user_message",
        "data": {"content": user_message, "session_id": session_id},
        "access_token": token,
    }
    websocket_handler.auth_service.get_user.return_value = user
    websocket_handler.session_manager.get_session.return_value = session
    websocket_handler.agency_manager.get_agency.return_value = (agency, None)
    websocket_handler.message_manager.get_messages.return_value = all_messages

    await websocket_handler._process_single_message(websocket, client_id)

    websocket.receive_json.assert_awaited_once()
    websocket_handler.auth_service.get_user.assert_called_once_with(token)
    websocket_handler.session_manager.get_session.assert_called_once_with(session_id)
    websocket_handler.agency_manager.get_agency.assert_awaited_once_with(session.agency_id, session.thread_ids, user.id)
    websocket_handler.session_manager.update_session_timestamp.assert_called_once_with(session_id)
    websocket_handler.message_manager.get_messages.assert_called_once_with(session_id)
    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {
            "type": "agent_response",
            "data": {
                "status": True,
                "message": "Message processed successfully",
                "data": [message.model_dump() for message in all_messages],
            },
            "connection_id": client_id,
        },
        client_id,
    )


@pytest.mark.asyncio
async def test_process_single_message_invalid_message_type(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"
    token = "valid_token"

    websocket.receive_json.return_value = {"type": "invalid_type", "data": {}, "access_token": token}

    await websocket_handler._process_single_message(websocket, client_id)

    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {"status": False, "message": "Invalid message type"}, client_id
    )


@pytest.mark.asyncio
async def test_process_single_message_user_message_missing_token(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"

    message = {"type": "user_message", "data": {"content": "User message", "session_id": "session_id"}}
    websocket.receive_json.return_value = message

    await websocket_handler._process_single_message(websocket, client_id)

    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {"status": False, "message": "Access token not provided"}, client_id
    )


@pytest.mark.asyncio
async def test_process_single_message_session_not_found(websocket_handler):
    websocket = AsyncMock(spec=WebSocket)
    client_id = "client_id"
    token = "token"
    session_id = "session_id"

    message = {
        "type": "user_message",
        "data": {"content": "User message", "session_id": session_id},
        "access_token": token,
    }
    websocket.receive_json.return_value = message

    with (
        patch.object(websocket_handler, "_authenticate", new_callable=AsyncMock),
        patch.object(websocket_handler, "_setup_agency", new_callable=AsyncMock, return_value=(None, None)),
    ):
        await websocket_handler._process_single_message(websocket, client_id)

    websocket_handler.connection_manager.send_message.assert_awaited_once_with(
        {"status": False, "message": "Session not found"}, client_id
    )
