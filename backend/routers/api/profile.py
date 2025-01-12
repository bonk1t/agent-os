import json
import os
from typing import Annotated

from fastapi import APIRouter, Body, Depends
from jsonref import requests

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_user_profile_manager
from backend.models.auth import User
from backend.models.response_models import UserProfileResponse
from backend.services.user_profile_manager import UserProfileManager

profile_router = APIRouter(tags=["user"])


@profile_router.get("/user/profile")
async def get_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
) -> UserProfileResponse:
    """
    Retrieve profile data associated with the current user.
    This endpoint fetches profile data stored for the authenticated user.
    """
    user_profile = user_profile_manager.get_user_profile(current_user.id)
    user_profile_data = {}
    if user_profile is not None:
        user_profile_data = {
            "first_name": user_profile.get("first_name"),
            "last_name": user_profile.get("last_name"),
            "email_subscription": user_profile.get("email_subscription")
            if user_profile.get("email_subscription") is not None
            else "",
        }

    return UserProfileResponse(data=user_profile_data)


@profile_router.put("/user/profile")
async def update_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    user_profile_fields: dict[str, str] = Body(...),
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
) -> UserProfileResponse:
    """
    Update or set profile data associated with the current user.

    This endpoint allows for updating the user's profile data.
    """
    user_profile = user_profile_manager.get_user_profile(current_user.id)

    previous_email_subscribe_value = str(user_profile.get("email_subscription") if user_profile is not None else "")
    requested_email_subscribe_value = str(user_profile_fields.get("email_subscription", ""))

    if validate_email_subscription_change(previous_email_subscribe_value, requested_email_subscribe_value):
        api_key = os.environ.get("MAILCHIMP_API_KEY", "")
        list_id = os.environ.get("MAILCHIMP_LIST_ID", "")
        email = current_user.email
        data = prepare_mailchimp_data(email, user_profile_fields)
        headers = get_mailchimp_headers(api_key)

        mailchimp_member_hash_id = str(
            user_profile.get("mail_chimp_member_hash_id") if user_profile is not None else ""
        )
        url = get_mailchimp_url(api_key, list_id, mailchimp_member_hash_id)

        member_id = update_mailchimp_subscription(url, headers, data, bool(mailchimp_member_hash_id))
        if member_id:
            user_profile_fields["mail_chimp_member_hash_id"] = member_id

    user_profile = await update_user_profile_in_db(user_profile_manager, current_user.id, user_profile_fields)
    if user_profile is None:
        user_profile = {}

    user_profile_data = {
        "first_name": user_profile.get("first_name"),
        "last_name": user_profile.get("last_name"),
        "email_subscription": user_profile.get("email_subscription")
        if user_profile.get("email_subscription") is not None
        else "",
    }

    return UserProfileResponse(message="Profile is updated successfully", data=user_profile_data)


def validate_email_subscription_change(previous_value: str, requested_value: str) -> bool:
    return bool(requested_value and (previous_value != requested_value))


def prepare_mailchimp_data(email: str, fields: dict[str, str]) -> dict:
    return {
        "email_address": email,
        "status": fields.get("email_subscription"),
        "merge_fields": {
            "FNAME": fields.get("first_name"),
            "LNAME": fields.get("last_name"),
        },
    }


def get_mailchimp_headers(api_key: str) -> dict:
    return {"Authorization": f"apikey {api_key}", "Content-Type": "application/json"}


def get_mailchimp_url(api_key: str, list_id: str, member_hash_id: str = "") -> str:
    dc = api_key.split("-")[-1]
    base_url = f"https://{dc}.api.mailchimp.com/3.0/lists/{list_id}/members/"
    return base_url + member_hash_id if member_hash_id else base_url


def update_mailchimp_subscription(url: str, headers: dict, data: dict, is_existing_member: bool) -> str | None:
    response = (
        requests.put(url, headers=headers, data=json.dumps(data))
        if is_existing_member
        else requests.post(url, headers=headers, data=json.dumps(data))
    )
    response.raise_for_status()  # Raise an error for bad HTTP status codes
    return response.json().get("id") if not is_existing_member else None


async def update_user_profile_in_db(
    user_profile_manager: UserProfileManager, user_id: str, fields: dict[str, str]
) -> dict:
    user_profile_manager.update_user_profile(user_id=user_id, fields=fields)
    result = user_profile_manager.get_user_profile(user_id)
    return result if result is not None else {}
