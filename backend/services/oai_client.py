import httpx
import openai

from backend.exceptions import UnsetVariableError
from backend.services.user_variable_manager import UserVariableManager


def get_openai_client(
    user_variable_manager: UserVariableManager | None = None, api_key: str | None = None
) -> openai.OpenAI:
    """
    Get an OpenAI client. Prefer Azure OpenAI if the Azure token is set.

    Args:
        user_variable_manager (UserVariableManager | None): The user variable manager to fetch API keys.
        api_key (str | None): The API key for OpenAI.

    Returns:
        openai.OpenAI: Configured OpenAI client.

    Raises:
        ValueError: If neither user_variable_manager nor api_key is provided, or if API keys are not set.
    """
    if user_variable_manager:
        try:
            azure_api_key = user_variable_manager.get_by_key("AZURE_OPENAI_API_KEY")
            api_version = user_variable_manager.get_by_key("OPENAI_API_VERSION")
            azure_endpoint = user_variable_manager.get_by_key("AZURE_OPENAI_ENDPOINT")
            return openai.AzureOpenAI(
                api_key=azure_api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                timeout=httpx.Timeout(60.0, read=30, connect=5.0),
                max_retries=5,
            )
        except UnsetVariableError:
            # Fall back to OpenAI setup if Azure key is not set
            pass

    if not api_key:
        if not user_variable_manager:
            raise ValueError("Either user_variable_manager or api_key must be provided")
        try:
            api_key = user_variable_manager.get_by_key("OPENAI_API_KEY")
        except UnsetVariableError as err:
            raise ValueError("API key not provided and no valid API key found in user variables") from err

    return openai.OpenAI(
        api_key=api_key,
        timeout=httpx.Timeout(60.0, read=30, connect=5.0),
        max_retries=5,
        default_headers={"OpenAI-Beta": "assistants=v2"},
    )
