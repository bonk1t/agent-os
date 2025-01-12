import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from backend.custom_skills.GetSQLDatabaseMetadata import GetSQLDatabaseMetadata
from backend.services.user_variable_manager import UserVariableManager


@pytest.fixture
def get_sql_database_metadata():
    return GetSQLDatabaseMetadata(database_name="test_db")


@pytest.fixture
def mock_user_variable_manager():
    return MagicMock(spec=UserVariableManager)


def test_run_success(get_sql_database_metadata, mock_user_variable_manager):
    # Arrange
    mock_user_variable_manager.get_by_key.side_effect = ["postgresql://username@host:port/", "password"]

    with (
        patch("backend.custom_skills.GetSQLDatabaseMetadata.create_engine") as mock_create_engine,
        patch("backend.custom_skills.GetSQLDatabaseMetadata.MetaData") as mock_metadata,
        patch(
            "backend.custom_skills.GetSQLDatabaseMetadata.UserVariableManager",
            return_value=mock_user_variable_manager,
        ),
    ):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_metadata_instance = MagicMock()
        mock_metadata.return_value = mock_metadata_instance

        mock_table = MagicMock()
        mock_column_id = MagicMock()
        mock_column_id.name = "id"
        mock_column_id.type = "INTEGER"
        mock_column_name = MagicMock()
        mock_column_name.name = "name"
        mock_column_name.type = "VARCHAR"
        mock_table.columns = [mock_column_id, mock_column_name]
        mock_metadata_instance.tables = {"users": mock_table}

        # Act
        result = get_sql_database_metadata.run()

        # Assert
        assert "Database Schema Information:" in result
        assert "Table: users" in result
        assert "Column: id, Type: INTEGER" in result
        assert "Column: name, Type: VARCHAR" in result
        mock_create_engine.assert_called_once_with(
            "postgresql://username@host:port/test_db", connect_args={"password": "password"}
        )
        mock_metadata_instance.reflect.assert_called_once_with(bind=mock_engine)
        mock_engine.dispose.assert_called_once()


def test_run_exception(get_sql_database_metadata, mock_user_variable_manager, caplog):
    # Arrange
    mock_user_variable_manager.get_by_key.side_effect = ["postgresql://username@host:port/", "password"]
    expected_error_message = "Error while listing tables and columns from database: Database connection error"
    expected_output = json.dumps({"error": expected_error_message})

    caplog.set_level(logging.INFO)

    with (
        patch("backend.custom_skills.GetSQLDatabaseMetadata.create_engine") as mock_create_engine,
        patch("backend.custom_skills.GetSQLDatabaseMetadata.MetaData") as mock_metadata,
        patch(
            "backend.custom_skills.GetSQLDatabaseMetadata.UserVariableManager",
            return_value=mock_user_variable_manager,
        ),
    ):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_metadata_instance = MagicMock()
        mock_metadata.return_value = mock_metadata_instance
        mock_metadata_instance.reflect.side_effect = Exception("Database connection error")

        # Act
        result = get_sql_database_metadata.run()

        # Assert
        assert result == expected_output
        assert expected_error_message in caplog.text
        mock_engine.dispose.assert_called_once()
