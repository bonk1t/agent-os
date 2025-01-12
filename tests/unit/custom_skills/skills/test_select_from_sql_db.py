import json
from unittest.mock import MagicMock, patch

from backend.custom_skills.SelectFromSQLDatabase import SelectFromSQLDatabase


@patch("backend.custom_skills.SelectFromSQLDatabase.UserVariableManager")
@patch("backend.custom_skills.SelectFromSQLDatabase.create_engine")
@patch("backend.custom_skills.SelectFromSQLDatabase.sessionmaker")
def test_select_from_db_success(mock_sessionmaker, mock_create_engine, mock_user_variable_manager):
    # Mock the user variable manager to return database credentials
    mock_variable_storage = MagicMock()
    mock_variable_storage.get_by_key.side_effect = [
        "postgresql://username@host:5432/",  # DATABASE_URL_PREFIX
        "secret",  # DATABASE_PASSWORD
    ]
    mock_user_variable_manager.return_value = mock_variable_storage

    # Mock the SQLAlchemy session
    mock_session_class = MagicMock()
    mock_session = mock_session_class.return_value.__enter__.return_value
    mock_result = [MagicMock(spec=["_asdict"]) for _ in range(1)]
    mock_result[0]._asdict.return_value = {"id": 1, "name": "Alice", "email": "alice@example.com"}
    mock_session.execute.return_value = iter(mock_result)
    mock_sessionmaker.return_value = mock_session_class
    mock_create_engine.return_value.dispose = MagicMock()

    tool = SelectFromSQLDatabase(
        database_name="testdb",
        table="users",
        columns=["id", "name", "email"],
        filters={"name": "Alice"},
        order_by="id",
        order_direction="ASC",
        limit=1,
    )
    response = tool.run()

    expected_result = json.dumps([{"id": 1, "name": "Alice", "email": "alice@example.com"}], indent=4, default=str)

    assert response == expected_result
    mock_session.execute.assert_called_once()


@patch("backend.custom_skills.SelectFromSQLDatabase.UserVariableManager")
@patch("backend.custom_skills.SelectFromSQLDatabase.create_engine")
@patch("backend.custom_skills.SelectFromSQLDatabase.sessionmaker")
def test_select_from_db_failure(mock_sessionmaker, mock_create_engine, mock_user_variable_manager):
    mock_variable_storage = MagicMock()
    mock_variable_storage.get_by_key.side_effect = ["postgresql://username@host:5432/", "secret"]
    mock_user_variable_manager.return_value = mock_variable_storage

    mock_session_class = MagicMock()
    mock_session = mock_session_class.return_value.__enter__.return_value
    mock_session.execute.side_effect = Exception("Database connection error")
    mock_sessionmaker.return_value = mock_session_class
    mock_create_engine.return_value.dispose = MagicMock()

    tool = SelectFromSQLDatabase(
        database_name="testdb",
        table="users",
        columns=["id", "name", "email"],
        filters={"name": "Alice"},
        order_by="id",
        order_direction="ASC",
        limit=1,
    )
    response = tool.run()

    assert json.loads(response) == {"error": "An error occurred while processing the request"}
