from agency_swarm import BaseTool
from pydantic import Field

from backend.settings import settings
from backend.utils import get_chat_completion

USER_PROMPT_PREFIX = "Please draft a proposal for the following project brief: \n"
SYSTEM_MESSAGE = """\
You are a professional proposal drafting assistant. \
Do not include any actual technologies or technical details into proposal unless \
specified in the project brief. Be concise.\
"""


class GenerateProposal(BaseTool):
    """Generate a proposal for a project based on a project brief.
    Remember that user does not have access to the output of this function.
    You must send it back to him after execution."""

    project_brief: str = Field(..., description="The project brief to generate a proposal for.")

    def run(self) -> str:
        user_prompt = f"{USER_PROMPT_PREFIX}{self.project_brief}"
        response = get_chat_completion(
            system_message=SYSTEM_MESSAGE, user_prompt=user_prompt, temperature=0.6, model=settings.gpt_model
        )
        return response
