import os
from pathlib import Path

from agency_swarm import BaseTool
from pydantic import Field

from backend.custom_skills.PrintFileContents import PrintFileContents
from backend.settings import settings
from backend.utils import get_chat_completion

SYSTEM_MESSAGE = """\
Your main job is to handle programming code from A FILE. \
The file's content is shown within triple backticks and has a FILE PATH as a title. \
It's vital to KEEP the FILE PATH. \
Here's what to do:
1. Start with a short SUMMARY of the file content.
2. KEEP important elements like non-trivial imports, function details, type hints, and key constants. \
Don't change these.
3. For classes, provide a brief SUMMARY in the docstrings, explaining the class's purpose and main logic.
4. Shorten and combine docstrings and comments into the function or method descriptions.
5. In functions or class methods, replace long code with a short SUMMARY in the docstrings, keeping the main logic.
6. Cut down long strings to keep things brief.

Your task is to create a concise version of the code, strictly keeping the structure, \
without extra comments or explanations. Focus on clarity and avoiding repeated information.\
"""


class SummarizeCode(BaseTool):
    """Summarize code using GPT-3. The skill uses the `PrintFileContents` skill to get the code to summarize."""

    file_name: Path = Field(
        ..., description="The name of the file to be summarized. It can be a relative or absolute path."
    )
    model: str = Field(default=settings.gpt_model, description="A model to use for summarization, defaults to gpt-4o")

    def run(self, api_key: str | None = None) -> str:
        code = PrintFileContents(file_name=self.file_name).run()
        output = get_chat_completion(
            system_message=SYSTEM_MESSAGE,
            user_prompt=code,
            temperature=0.0,
            model=self.model,
            api_key=api_key,
        )
        return output


if __name__ == "__main__":
    print(
        SummarizeCode(
            file_name="example.py",
        ).run(api_key=os.getenv("API_KEY"))
    )
