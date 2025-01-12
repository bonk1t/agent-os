from unittest.mock import Mock, patch

import pytest

from backend.custom_skills.GenerateProposal import GenerateProposal


@pytest.fixture
def mock_openai_response():
    class MockOpenAIResponse:
        choices = [Mock(message=Mock(content="Mocked Proposal"))]

    return MockOpenAIResponse()


@patch("backend.utils.get_openai_client")
def test_generate_proposal_with_valid_brief(mock_openai_client, mock_openai_response):
    mock_openai_client.return_value.chat.completions.create.return_value = mock_openai_response
    proposal_skill = GenerateProposal(project_brief="Create a web application.")
    response = proposal_skill.run()
    assert response == "Mocked Proposal"
    mock_openai_client.assert_called_once()


@patch("backend.utils.get_openai_client", side_effect=Exception("API failed"))
def test_generate_proposal_with_api_failure(mock_openai_client):
    proposal_skill = GenerateProposal(project_brief="Create a VR game.")
    with pytest.raises(Exception) as exc_info:
        proposal_skill.run()
    assert "API failed" in str(exc_info.value)
    mock_openai_client.assert_called_once()
