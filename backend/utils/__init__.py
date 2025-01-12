import hashlib
import json
import logging
import sys
from pathlib import Path

import firebase_admin
import openai
import tiktoken
from firebase_admin import credentials
from pydantic import BaseModel

from backend.repositories.agent_flow_spec_storage import AgentFlowSpecStorage
from backend.repositories.user_variable_storage import UserVariableStorage
from backend.services.oai_client import get_openai_client
from backend.services.user_variable_manager import UserVariableManager
from backend.settings import settings

logger = logging.getLogger(__name__)


def init_firebase_app():
    """Initialize Firebase app."""
    if settings.google_credentials:
        cred_json = json.loads(settings.google_credentials)
        cred = credentials.Certificate(cred_json)
        firebase_admin.initialize_app(cred)


def init_openai_client():
    """Initialize the OpenAI client."""
    user_variable_manager = UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())
    return get_openai_client(user_variable_manager=user_variable_manager)


def patch_openai_client():
    """Patch the agency_swarm's openai client to use the user variable manager."""
    sys.modules["agency_swarm.util.oai"].get_openai_client = init_openai_client
    sys.modules["agency_swarm.threads.thread"].get_openai_client = init_openai_client
    sys.modules["agency_swarm.agents.agent"].get_openai_client = init_openai_client
    sys.modules["agency_swarm"].get_openai_client = init_openai_client


def init_webserver_folders(root_file_path: Path) -> dict[str, Path]:
    """
    Initialize folders needed for a web server, such as static file directories
    and user-specific data directories.

    :param root_file_path: The root directory where webserver folders will be created
    :return: A dictionary with the path of each created folder
    """
    static_folder_root = root_file_path / "ui"
    static_folder_root.mkdir(parents=True, exist_ok=True)
    folders = {
        "static_folder_root": static_folder_root,
    }
    return folders


def get_chat_completion(system_message: str, user_prompt: str, model: str, api_key: str | None = None, **kwargs) -> str:
    """Generate a chat completion based on a prompt and a system message.
    This function is a wrapper around the OpenAI API."""
    if api_key:
        client = get_openai_client(api_key=api_key)
    else:
        client = get_openai_client(
            user_variable_manager=UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())
        )
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system" if not model.startswith("o") else "user", "content": system_message},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )
    return completion.choices[0].message.content


def get_chat_completion_structured(
    system_message: str, user_prompt: str, model: str, response_format: BaseModel, api_key: str | None = None, **kwargs
) -> BaseModel:
    """Generate a structured chat completion based on a prompt and a system message.
    This function is a wrapper around the OpenAI API that returns parsed structured data."""
    if api_key:
        client: openai.OpenAI = get_openai_client(api_key=api_key)
    else:
        client = get_openai_client(
            user_variable_manager=UserVariableManager(UserVariableStorage(), AgentFlowSpecStorage())
        )

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
        **kwargs,
    )

    return completion.choices[0].message.parsed


def tokenize(text: str, model: str) -> list[int]:
    """Tokenize a string using tiktoken tokenizer."""
    return tiktoken.encoding_for_model(model).encode(text)


def get_token_count(text: str, model: str) -> int:
    """Get the number of tokens using tiktoken tokenizer."""
    return len(tokenize(text, model))


def chunk_input_with_token_limit(input_str: str, max_tokens: int, delimiter: str, model: str) -> list:
    chunks = []
    parts = input_str.split(delimiter)
    current_chunk: list[str] = []

    current_tokens = 0
    for part in parts:
        part_token_count = get_token_count(part + delimiter, model)
        if current_tokens + part_token_count > max_tokens:
            new_chunk = delimiter.join(current_chunk)
            if get_token_count(new_chunk, model) > max_tokens:
                logger.warning(f"Part of the input is longer than {max_tokens} tokens.")
                new_chunk = truncate_oversized_chunk(new_chunk, max_tokens=max_tokens, delimiter=delimiter, model=model)
            chunks.append(new_chunk + delimiter)
            current_chunk = [part]
            current_tokens = part_token_count
        else:
            current_chunk.append(part)
            current_tokens += part_token_count

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(delimiter.join(current_chunk) + delimiter)

    return chunks


def truncate_oversized_chunk(chunk: str, max_tokens: int, delimiter: str, model: str) -> str:
    """Truncate the chunk if it is longer than max_tokens."""
    tokens = tokenize(chunk + delimiter, model)
    if len(tokens) > max_tokens:
        tokens = tokens[: max_tokens - get_token_count(delimiter, model)]
        chunk = tiktoken.encoding_for_model(model).decode(tokens)
        chunk += delimiter
    return chunk


def sanitize_id(input_string: str) -> str:
    """Sanitize an ID to prevent injection attacks. Leave only alphanumeric characters and "_"."""
    input_string = input_string.replace("\r\n", "").replace("\n", "")
    return "".join(c for c in input_string if c.isalnum() or c == "_")


def hash_string(input_string: str) -> str:
    """Hash a string using SHA-256."""
    return hashlib.sha256(input_string.encode("utf-8")).hexdigest()
