from datetime import UTC, datetime
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.models.session_config import SessionConfig
from backend.services.session_manager import SessionManager


# Fixtures
@pytest.fixture
def agency_mock():
    agency = MagicMock()
    agency.main_thread.id = "main_thread_id"
    return agency


@pytest.fixture
def session_storage_mock():
    return MagicMock()


@pytest.fixture
def agency_storage_mock():
    return MagicMock()


@pytest.fixture
def session_manager(session_storage_mock, agency_storage_mock):
    return SessionManager(
        session_storage=session_storage_mock,
        agency_storage=agency_storage_mock,
        user_secret_manager=MagicMock(),
        session_adapter=MagicMock(),
    )


# Tests
def test_create_session(agency_mock, session_manager, session_storage_mock):
    session_id = session_manager.create_session(agency_mock, "agency_id", "user_id", thread_ids={})
    assert session_id == "main_thread_id", "The session ID should be the ID of the main thread."
    expected_session_config = SessionConfig(
        id="main_thread_id",
        user_id="user_id",
        agency_id="agency_id",
        timestamp=datetime.now(UTC).isoformat(),
    )
    expected_session_config.timestamp = mock.ANY
    session_storage_mock.save.assert_called_once_with(expected_session_config)


def test_delete_session(session_manager, session_storage_mock):
    session_manager.delete_session("session_id")
    session_storage_mock.delete.assert_called_once_with("session_id")


def test_delete_sessions_by_agency_id(session_manager, session_storage_mock):
    session_manager.delete_sessions_by_agency_id("agency_id")
    session_storage_mock.delete_by_agency_id.assert_called_once_with("agency_id")


def test_get_sessions_for_user(session_manager, session_storage_mock):
    session_manager.get_sessions_for_user("user_id")
    session_storage_mock.load_by_user_id.assert_called_once_with("user_id")


def test_validate_agency_permissions(session_manager, agency_storage_mock):
    agency_storage_mock.load_by_id.return_value = MagicMock(user_id="user_id")
    session_manager.validate_agency_permissions("agency_id", "user_id")
    agency_storage_mock.load_by_id.assert_called_once_with("agency_id")


def test_validate_agency_permissions_raises_404(session_manager, agency_storage_mock):
    agency_storage_mock.load_by_id.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        session_manager.validate_agency_permissions("agency_id", "user_id")
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND


def test_validate_agency_permissions_raises_403(session_manager, agency_storage_mock):
    agency_storage_mock.load_by_id.return_value = MagicMock(user_id="another_user_id")
    with pytest.raises(HTTPException) as exc_info:
        session_manager.validate_agency_permissions("agency_id", "user_id")
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
