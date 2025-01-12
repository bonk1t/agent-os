from unittest.mock import Mock, patch

import pytest

from backend.custom_skills.SummarizeCode import SummarizeCode


@pytest.fixture
def mock_openai_response():
    class MockCompletion:
        message = Mock(content="Summary of the code")

    class MockOpenAIResponse:
        choices = [MockCompletion()]

    return MockOpenAIResponse()


@patch("backend.utils.get_openai_client")
def test_summarize_code_with_valid_file(mock_openai_client, mock_openai_response, tmp_path):
    # Create a simple Python file
    file_path = tmp_path / "test.py"
    file_path.write_text('print("Hello, World!")')
    mock_openai_client.return_value.chat.completions.create.return_value = mock_openai_response

    summarize_skill = SummarizeCode(file_name=str(file_path))
    results = summarize_skill.run()
    assert "Summary of the code" in results
    mock_openai_client.assert_called_once()


@patch("backend.utils.get_openai_client", side_effect=Exception("API failed"))
def test_summarize_code_with_api_failure(mock_openai_client, tmp_path):
    file_path = tmp_path / "test.py"
    file_path.write_text('print("Hello, World!")')
    summarize_skill = SummarizeCode(file_name=str(file_path))
    with pytest.raises(Exception) as exc_info:
        summarize_skill.run()
    assert "API failed" in str(exc_info.value)
    mock_openai_client.assert_called_once()
