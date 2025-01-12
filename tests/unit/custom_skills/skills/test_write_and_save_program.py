from pathlib import Path
from unittest.mock import mock_open, patch

from backend.constants import AGENCY_DATA_DIR
from backend.custom_skills.WriteAndSaveProgram import File, WriteAndSaveProgram
from tests.testing_utils.constants import TEST_AGENCY_ID


@patch("backend.services.context_vars_manager.ContextEnvVarsManager.get", return_value=TEST_AGENCY_ID)
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path.mkdir")
def test_write_and_save_program_with_valid_files(mock_get, mock_mkdir, mock_file):
    files = [
        File(file_name="test1.py", body='print("Hello")', chain_of_thought=""),
        File(file_name="test2.py", body='print("World")', chain_of_thought=""),
    ]
    save_program_skill = WriteAndSaveProgram(files=files, chain_of_thought="")
    response = save_program_skill.run()

    expected_path1 = Path(AGENCY_DATA_DIR / TEST_AGENCY_ID / "test1.py").as_posix()
    expected_path2 = Path(AGENCY_DATA_DIR / TEST_AGENCY_ID / "test2.py").as_posix()

    assert f"File written to {expected_path1}" in response
    assert f"File written to {expected_path2}" in response

    mock_get.assert_called()
    mock_mkdir.assert_called()
    mock_file.assert_called()


@patch("builtins.open", new_callable=mock_open)
def test_write_and_save_program_with_invalid_path(mock_file):
    files = [File(file_name="../invalid/path.py", body='print("Fail")', chain_of_thought="")]
    save_program_skill = WriteAndSaveProgram(files=files, chain_of_thought="")
    response = save_program_skill.run()

    assert "Invalid file path" in response
    mock_file.assert_not_called()
