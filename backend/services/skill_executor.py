import json
import logging
from typing import Any, Dict, Type

from agency_swarm import BaseTool

from backend import custom_skills
from backend.models.skill_config import SkillConfig
from backend.repositories.skill_config_storage import SkillConfigStorage
from backend.services.sandbox_manager import sandbox_manager
from backend.settings import settings
from backend.utils import get_chat_completion

SKILL_SUMMARY_SYSTEM_MESSAGE = """\
As a supportive assistant, ensure your responses are concise,
confined to a single sentence, and rigorously comply with the specified instructions.\
"""
USER_PROMPT = "In one succinct sentence, describe the functionality of the skill provided below:\n"

logger = logging.getLogger(__name__)


class SkillExecutor:
    SYSTEM_MESSAGE = """\
You are an assistant that responds with JSON only. You are presented with a user prompt and a function specification, \
and you MUST return the function call parameters in JSON format.
For example, if the function has parameters file_name and file_size, \
and the user prompt is ```file name is test.txt, and the size is 1MB```, \
then the function call parameters are {\"file_name\": \"test.txt\", \"file_size\": \"1MB\"}
The function call parameters must be returned in JSON format.\
"""
    USER_PROMPT_PREFIX = "Return the function call parameters in JSON format based on the following user prompt: "

    def __init__(self):
        self.skill_config_storage = SkillConfigStorage()

    async def execute_skill(self, skill_name: str, user_prompt: str) -> str:
        """
        Get the skill from Firestore, parse arguments using GPT, 
        and execute it in a secure E2B sandbox.
        """
        try:
            # Get skill metadata (to extract openai_schema)
            skill_class = self._get_skill_class(skill_name)
            
            # Get the skill config from Firestore
            skill_configs = self.skill_config_storage.load_by_titles([skill_name])
            if not skill_configs:
                return f"Error: Skill {skill_name} not found in storage"
            
            skill_config = skill_configs[0]
            
            # Get arguments using GPT
            args_str = self._get_skill_arguments(json.dumps(skill_class.openai_schema), user_prompt)
            args_dict = json.loads(args_str)
            
            # Execute the skill in a secure E2B sandbox
            logger.info(f"Executing skill {skill_name} with arguments: {args_dict}")
            result = await sandbox_manager.execute_skill_from_config(skill_config, args_dict)
            
            # Extract the final result - look for the "Output from skill:" line
            output_lines = result.strip().split('\n')
            for line in output_lines:
                if line.startswith("Output from skill:"):
                    return line.replace("Output from skill:", "").strip()
                    
            # If we can't find the output line, return the full output
            return result
            
        except Exception as e:
            logger.exception(f"Error executing skill {skill_name}: {e}")
            error_message = f"Error: {e}"
            if "For further information visit" in error_message:
                error_message = error_message.split("For further information visit")[0]
            return error_message

    def _get_skill_arguments(self, function_spec: str, user_prompt: str) -> str:
        user_prompt = (
            f"{self.USER_PROMPT_PREFIX}\n```\n{user_prompt}\n```. \nThe function specification:\n```{function_spec}```"
        )
        args_str = get_chat_completion(
            system_message=self.SYSTEM_MESSAGE, user_prompt=user_prompt, temperature=0.0, model=settings.gpt_model
        )
        return args_str.strip("`json\n ").replace("\n", "")

    @staticmethod
    def _get_skill_class(skill_name: str) -> Type[BaseTool]:
        """Get a skill class by name from SKILL_MAPPING"""
        try:
            if skill_name not in custom_skills.SKILL_MAPPING:
                raise KeyError(f"Skill not found: {skill_name}")
            return custom_skills.SKILL_MAPPING[skill_name]
        except Exception as e:
            logger.exception(f"Error getting skill: {skill_name}")
            raise RuntimeError(f"Skill not found: {skill_name}") from e
