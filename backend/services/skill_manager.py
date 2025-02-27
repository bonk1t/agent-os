import ast
import importlib
import logging
import os
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.exceptions import NotFoundError, UnsetVariableError
from backend.models.skill_config import SkillConfig
from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.utils import get_chat_completion, get_chat_completion_structured

logger = logging.getLogger(__name__)

MAX_SKILL_LINES = 200

SKILL_SAFETY_SYSTEM_MESSAGE = """\
You are a security expert evaluating custom skills/tools for an AI system. \
Your task is to determine if the skill is safe to use.
Evaluate the skill based on these criteria:
1. No dangerous file system operations (no arbitrary file reading/writing/deleting)
2. No malicious network requests or potential for data exfiltration
3. No attempts to circumvent system protections or security measures
4. Clear and understandable purpose and functionality
5. No potential for executing arbitrary code or commands

Respond with a JSON object.
"""
PARSE_SAFETY_EVALUATION_SYSTEM_MESSAGE = """\
You are a JSON parser. \
Format the following response into a valid JSON object with 'is_safe' (boolean) and 'reason' (string) fields.
"""


class SafetyEvaluation(BaseModel):
    is_safe: bool = Field(..., description="Whether the skill is safe to use")
    reason: str = Field(..., description="A concise explanation of why the skill is safe or unsafe")


class FileSystem(Protocol):
    """Protocol for file system operations."""

    def write_file(self, path: Path, content: str) -> None:
        """Write content to a file."""
        ...

    def remove_file(self, path: Path) -> None:
        """Remove a file."""
        ...

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        ...


class RealFileSystem:
    """Real file system implementation."""

    def write_file(self, path: Path, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    def remove_file(self, path: Path) -> None:
        if path.exists():
            os.remove(path)

    def file_exists(self, path: Path) -> bool:
        return path.exists()


class SkillManager:
    def __init__(self, storage: SkillConfigStorage, fs: FileSystem | None = None):
        self.storage = storage
        self.fs = fs or RealFileSystem()
        # Get the custom_skills directory path
        self.skills_dir = Path(__file__).parent.parent / "custom_skills"

    def _extract_class_name(self, code: str) -> str:
        """Extract the first class name from the Python code that inherits from BaseTool."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "BaseTool":
                            return node.name
            raise ValueError("No class inheriting from BaseTool found in the code")
        except Exception as e:
            logger.error(f"Error parsing skill code: {e}")
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=f"Invalid skill code: {str(e)}") from e

    def _validate_skill_code(self, code: str) -> tuple[str, str]:
        """Validate the skill code and return the class name and module name."""
        class_name = self._extract_class_name(code)
        module_name = f"backend.custom_skills.{class_name.lower()}"

        # Verify imports and basic syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=f"Invalid Python syntax in skill code: {str(e)}"
            ) from e

        return class_name, module_name

    def _save_skill_to_file(self, config: SkillConfig) -> None:
        """Save the skill code to a Python file in the custom_skills directory."""
        # Validate the code and get class/module names
        class_name, module_name = self._validate_skill_code(config.content)

        # Create filename from the class name
        filename = f"{class_name.lower()}.py"
        file_path = self.skills_dir / filename

        try:
            self.fs.write_file(file_path, config.content)
        except Exception as e:
            logger.error(f"Error saving skill file: {e}")
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to save skill file: {str(e)}"
            ) from e

    def _reload_and_validate_skill(self, class_name: str, module_name: str) -> None:
        """Reload modules and validate skill registration."""
        try:
            # First reload the skill registry to clear existing registrations
            from backend.custom_skills import skill_registry

            skill_registry.reload()

            # Force reload the specific module
            module = importlib.import_module(module_name)
            importlib.reload(module)

            # Verify the skill is properly registered
            if not skill_registry.is_registered(class_name):
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=f"Skill class {class_name} was not properly registered in skill registry",
                )

        except ImportError as e:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=f"Failed to import skill module: {str(e)}"
            ) from e
        except Exception as e:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e

    def _initialize_skill(self, config: SkillConfig) -> tuple[str, str]:
        """Initialize a skill by saving it to file and validating its registration."""
        # Validate the code and get class/module names
        class_name, module_name = self._validate_skill_code(config.content)

        try:
            # Save the file
            self._save_skill_to_file(config)

            # Validate the skill
            self._reload_and_validate_skill(class_name, module_name)

            return class_name, module_name
        except Exception as e:
            # Clean up the file if anything fails
            filename = f"{class_name.lower()}.py"
            file_path = self.skills_dir / filename
            if self.fs.file_exists(file_path):
                self.fs.remove_file(file_path)
            raise e

    def _delete_skill_file(self, config: SkillConfig) -> None:
        """Delete the skill's Python file from the custom_skills directory."""
        try:
            class_name = self._extract_class_name(config.content)
            filename = f"{class_name.lower()}.py"
            file_path = self.skills_dir / filename

            if self.fs.file_exists(file_path):
                self.fs.remove_file(file_path)
        except Exception as e:
            logger.error(f"Error deleting skill file: {e}")
            # Don't raise an exception here as the file might not exist

    def get_skill_list(self, current_user_id: str) -> list[SkillConfig]:
        """Get a list of configs for the skills owned by the current user and template (public) skills."""
        skills = self.storage.load_by_user_id(current_user_id) + self.storage.load_by_user_id(None)
        sorted_skills = sorted(skills, key=lambda x: x.timestamp, reverse=True)
        return sorted_skills

    def get_skill_config(self, id_: str) -> SkillConfig:
        """Get a skill configuration by ID."""
        config_db = self.storage.load_by_id(id_)
        if not config_db:
            raise NotFoundError("Skill", id_)
        return config_db

    def _check_skill_size(self, code: str) -> None:
        """Check if the skill code is within the allowed size limit."""
        num_lines = len(code.splitlines())
        if num_lines > MAX_SKILL_LINES:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Skill code exceeds maximum allowed lines ({MAX_SKILL_LINES}). Current size: {num_lines} lines",
            )

    def _evaluate_skill_safety(self, config: SkillConfig) -> tuple[bool, str]:
        """Evaluate if a skill is safe to use using o3-mini.

        :param config: The skill configuration to evaluate
        :return: A tuple of (is_safe, reason)
        :raises: HTTPException if there's an error evaluating the skill
        """
        # Check skill size first
        self._check_skill_size(config.content)

        # Prepare the skill description for evaluation
        skill_description = f"""
Title: {config.title}
Description: {config.description}
Code:
```python
{config.content}
```
"""
        try:
            # First call to get the evaluation
            initial_response = get_chat_completion(
                system_message=SKILL_SAFETY_SYSTEM_MESSAGE,
                user_prompt=skill_description,
                model="o3-mini",
            )

            # Second call to parse the response into structured format
            parsed_response: SafetyEvaluation = get_chat_completion_structured(
                system_message=PARSE_SAFETY_EVALUATION_SYSTEM_MESSAGE,
                user_prompt=initial_response,
                model="gpt-4o-mini",
                response_format=SafetyEvaluation,
            )

            return parsed_response.is_safe, parsed_response.reason
        except UnsetVariableError as e:
            # Specifically handle missing API key error
            logger.error("API key error: %s", str(e))
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Cannot evaluate skill safety: {str(e)}. Please set up your API key in the settings.",
            ) from e
        except Exception as e:
            logger.error("Error evaluating skill safety: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=f"Error evaluating skill safety: {str(e)}"
            ) from e

    def create_or_update_skill(self, config: SkillConfig, current_user_id: str) -> str:
        """Create or update a skill configuration."""
        # Support template configs
        if not config.user_id:
            logger.info(f"Creating skill for user: {current_user_id}, skill: {config.title}")
            config.id = None

        # Check permissions if updating existing skill
        config_db = None
        if config.id:
            config_db = self.get_skill_config(config.id)
            self.check_user_permissions(config_db, current_user_id)

        # Ensure the skill is associated with the current user
        config.user_id = current_user_id
        config.timestamp = datetime.now(UTC).isoformat()

        # Check if code has changed from previous version
        if config_db and config_db.content == config.content:
            # Evaluate skill safety
            is_safe, reason = self._evaluate_skill_safety(config)
            if not is_safe:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=f"Skill not safe: {reason}",
                )

        # Initialize the skill
        # self._initialize_skill(config)

        # Save the approved skill to storage
        skill_id = self.storage.save(config)
        return skill_id

    def delete_skill(self, id_: str, current_user_id: str) -> None:
        """Delete a skill configuration."""
        config = self.get_skill_config(id_)
        self.check_user_permissions(config, current_user_id)
        # Delete the skill file before removing from storage
        self._delete_skill_file(config)
        self.storage.delete(id_)

    @staticmethod
    def check_user_permissions(config: SkillConfig, current_user_id: str) -> None:
        if config.user_id != current_user_id:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="You don't have permissions to access this skill"
            )
