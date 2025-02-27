import json
import logging
import os

from agency_swarm import BaseTool
from e2b_code_interpreter import Sandbox

from backend import custom_skills
from backend.models.skill_config import SkillConfig
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

    def execute_skill(self, skill: SkillConfig, user_prompt: str):
        """
        Import the skill from custom_skills package, initialize it (using GPT to fill in kwargs), and run it
        """
        skill_class = BaseTool
        skill_args = self._get_skill_arguments(json.dumps(skill_class.openai_schema), user_prompt)
        return self._execute_skill(skill, skill_args)

    def _get_skill_arguments(self, function_spec: str, user_prompt: str) -> str:
        user_prompt = (
            f"{self.USER_PROMPT_PREFIX}\n```\n{user_prompt}\n```. \nThe function specification:\n```{function_spec}```"
        )
        args_str = get_chat_completion(
            system_message=self.SYSTEM_MESSAGE, user_prompt=user_prompt, temperature=0.0, model=settings.gpt_model
        )
        return args_str.strip("`json\n ").replace("\n", "")

    @staticmethod
    def _get_skill_class(skill_name: str) -> BaseTool:
        """Get a skill class by name from SKILL_MAPPING"""
        try:
            if skill_name not in custom_skills.SKILL_MAPPING:
                raise KeyError(f"Skill not found: {skill_name}")
            return custom_skills.SKILL_MAPPING[skill_name]
        except Exception as e:
            logger.exception(f"Error getting skill: {skill_name}")
            raise RuntimeError(f"Skill not found: {skill_name}") from e

    @staticmethod
    def _execute_skill(skill: SkillConfig, args: str) -> str | None:
        if not skill:
            return f"Error: Skill not found"

        try:
            # Ensure args are properly parsed
            parsed_args = json.loads(args)

            # Initialize E2B sandbox
            api_key = os.environ.get("E2B_API_KEY", "")
            sandbox = Sandbox(api_key=api_key)

            # Dynamically import the correct class using the skill id
            try:

                # Get the class source code dynamically
                class_code = skill.content
            except ModuleNotFoundError as e:
                return f"Error: {str(e)}"

            # Embed the class code and skill execution inside the sandbox
            script = f"""
            import json
            from agency_swarm import BaseTool

            {class_code}  # Embed the class code

            # Initialize the skill with provided arguments
            skill_instance = {skill.title}(**{parsed_args})

            # Run the skill and print output
            print(skill_instance.run())
            """

            # Run script inside E2B sandbox
            sandbox.commands.run("pip install agency_swarm")
            result = sandbox.run_code(script)
            return result.logs.stdout[0].strip()

        except Exception as e:
            error_message = f"Error: {e}"
            return error_message
