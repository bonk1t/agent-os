from unittest.mock import MagicMock, patch

from backend.custom_skills.SaveLeadToAirtable import SaveLeadToAirtable


@patch(
    "backend.custom_skills.SaveLeadToAirtable.UserVariableManager.get_by_key",
    side_effect=["fake_base_id", "fake_table_id", "fake_token"],
)
@patch("pyairtable.Api.table")
def test_save_lead_to_airtable_success(mock_table, mock_get_by_key):
    mock_table_instance = MagicMock()
    mock_table_instance.create.return_value = {"id": "fake_id", "createdTime": "fake_time"}
    mock_table.return_value = mock_table_instance

    skill = SaveLeadToAirtable(name="Jane Doe", email="jane@test.com", lead_details="Interested in service Y")
    response = skill.run()

    assert "id: fake_id, createdTime: fake_time" in response

    mock_get_by_key.assert_called_with("AIRTABLE_TOKEN")


@patch(
    "backend.custom_skills.SaveLeadToAirtable.UserVariableManager.get_by_key",
    side_effect=["fake_base_id", "fake_table_id", "fake_token"],
)
@patch("pyairtable.Api.table")
def test_save_lead_to_airtable_failure(mock_table, mock_get_by_key):
    mock_table_instance = MagicMock()
    mock_table_instance.create.side_effect = Exception("API error")
    mock_table.return_value = mock_table_instance

    skill = SaveLeadToAirtable(name="John Smith", email="johnsmith@test.com", lead_details="Looking for consulting.")
    response = skill.run()

    assert "Error while saving lead to Airtable" in response

    mock_get_by_key.assert_called_with("AIRTABLE_TOKEN")
