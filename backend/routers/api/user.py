from typing import Annotated

from fastapi import APIRouter, Body, Depends

from backend.dependencies.auth import get_current_user
from backend.dependencies.dependencies import get_user_variable_manager
from backend.models.auth import User
from backend.models.response_models import UserVariablesResponse
from backend.services.user_variable_manager import UserVariableManager

user_router = APIRouter(tags=["user"])


@user_router.get("/user/settings/variables")
async def get_variables(
    current_user: Annotated[User, Depends(get_current_user)],
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
) -> UserVariablesResponse:
    """
    Retrieve a list of variable names associated with the current user.
    This endpoint fetches the names of all variables stored for the authenticated user. It does not return the values,
    ensuring sensitive information remains secure.
    """
    user_variables = user_variable_manager.get_variable_names(current_user.id)
    return UserVariablesResponse(data=user_variables)


@user_router.put("/user/settings/variables")
async def update_variables(
    current_user: Annotated[User, Depends(get_current_user)],
    user_variables: dict[str, str] = Body(...),
    user_variable_manager: UserVariableManager = Depends(get_user_variable_manager),
) -> UserVariablesResponse:
    """
    Update or create the variables associated with the current user.

    This endpoint allows for updating the user's variables.
    Existing variables are updated based on the keys provided in the request body.
    This functionality supports partial updates; items variables "" values remain unchanged.
    """
    response = user_variable_manager.create_or_update_variables(user_id=current_user.id, variables=user_variables)
    message = "Variables updated successfully"
    if not response:
        message = "Please delete all agents and teams to update the Open AI API key"

    user_variable_names = user_variable_manager.get_variable_names(current_user.id)
    return UserVariablesResponse(status=response, message=message, data=user_variable_names)
