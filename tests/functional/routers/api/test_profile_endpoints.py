from unittest.mock import patch

import pytest

from backend.repositories.user_profile_storage import UserProfileStorage
from backend.services.user_profile_manager import UserProfileManager
from tests.testing_utils import TEST_USER_ID


@pytest.fixture
@pytest.mark.usefixtures("mock_firestore_client")
def user_profile_manager():
    yield UserProfileManager(
        user_profile_storage=UserProfileStorage(),
    )


@pytest.mark.usefixtures("mock_get_current_user")
def test_get_user_profile(client, mock_firestore_client):
    mock_firestore_client.setup_mock_data(
        "user_profiles", TEST_USER_ID, {"first_name": "John", "last_name": "Doe", "email_subscription": "subscribed"}
    )
    response = client.get("/api/user/profile")
    assert response.status_code == 200
    assert response.json() == {
        "status": True,
        "message": "Success",
        "data": {"first_name": "John", "last_name": "Doe", "email_subscription": "subscribed"},
    }


@pytest.mark.usefixtures("mock_get_current_user")
async def test_update_user_profile(client, mock_firestore_client, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv("MAILCHIMP_API_KEY", "testapikey-us1")
    monkeypatch.setenv("MAILCHIMP_LIST_ID", "testlistid")

    update_data = {"first_name": "Jane", "last_name": "Doe", "email_subscription": "unsubscribed"}

    with patch("jsonref.requests.post") as mock_post, patch("jsonref.requests.put") as mock_put:
        response = client.put("/api/user/profile", json=update_data)

        assert response.status_code == 200
        assert response.json() == {
            "status": True,
            "message": "Profile is updated successfully",
            "data": {"first_name": "Jane", "last_name": "Doe", "email_subscription": "unsubscribed"},
        }

        # Ensure the correct calls were made to the Mailchimp API
        mock_post.assert_called_once()
        mock_put.assert_not_called()
        user_profile = await user_profile_manager.get_user_profile(TEST_USER_ID)
        assert user_profile.first_name == "Jane"
