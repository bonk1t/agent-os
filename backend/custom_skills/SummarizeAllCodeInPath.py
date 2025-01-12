import os
from pathlib import Path

from agency_swarm import BaseTool
from pydantic import Field

from backend.custom_skills.PrintAllFilesInPath import PrintAllFilesInPath
from backend.settings import settings
from backend.utils import chunk_input_with_token_limit, get_chat_completion

SYSTEM_MESSAGE = """\
Your main job is to handle programming code from SEVERAL FILES. \
Each file's content is shown within triple backticks and has a FILE PATH as a title. \
It's vital to KEEP the FILE PATHS. Here's what to do:
1. ALWAYS KEEP the FILE PATHS for each file.
2. Start each file with a short SUMMARY of its content. Mention important points but don't repeat details found later.
3. KEEP important elements like non-trivial imports, function details, type hints, and key constants. \
Don't change these.
4. In functions or class methods, replace long code with a short SUMMARY in the docstrings, keeping the main logic.
5. Shorten and combine docstrings and comments into the function or method descriptions.
6. For classes, provide a brief SUMMARY in the docstrings, explaining the class's purpose and main logic.
7. Cut down long strings to keep things brief.
8. If there's a comment about "truncated output" at the end, KEEP it.

Your task is to create a concise version of the code, strictly keeping the FILE PATHS and structure, \
without extra comments or explanations. Focus on clarity and avoiding repeated information within each file.\
"""


class SummarizeAllCodeInPath(BaseTool):
    """Summarize code using GPT-3. The skill uses the `PrintAllFilesInPath` skill to get the code to summarize.
    The parameters are: start_path, file_extensions, exclude_directories.
    Directory traversal is not allowed (you cannot read /* or ../*).
    """

    start_path: Path = Field(
        default_factory=Path.cwd,
        description="The starting path to search for files, defaults to the current working directory. "
        "Can be a filename or a directory.",
    )
    file_extensions: list[str] = Field(
        default_factory=list,
        description="List of file extensions to include in the tree. If empty, all files will be included. "
        "Examples are ['.py', '.txt', '.md'].",
    )
    exclude_directories: list[str] | None = Field(
        default_factory=list,
        description="List of directories to exclude from the search. Examples are ['__pycache__', '.git'].",
    )
    truncate_to: int = Field(
        default=None,
        description="Truncate the output to this many characters. If None or skipped, the output is not truncated.",
    )
    model: str = Field(default=settings.gpt_model, description="A model to use for summarization, defaults to gpt-4o")

    def run(self, api_key: str | None = None) -> str:
        """Run the skill and return the output."""
        delimiter = "\n\n```\n"
        full_code = PrintAllFilesInPath(
            start_path=self.start_path,
            file_extensions=self.file_extensions,
            exclude_directories=self.exclude_directories,
        ).run()

        # Chunk the input based on token limit
        chunks = chunk_input_with_token_limit(full_code, max_tokens=16385 // 2, delimiter=delimiter, model=self.model)

        outputs = []
        for chunk in chunks:
            output = get_chat_completion(
                system_message=SYSTEM_MESSAGE,
                user_prompt=chunk,
                temperature=0.0,
                model=self.model,
                api_key=api_key,
            )
            outputs.append(output)

        # Concatenate and possibly truncate outputs
        concatenated_output = delimiter.join(outputs)
        if self.truncate_to and len(concatenated_output) > self.truncate_to:
            concatenated_output = (
                concatenated_output[: self.truncate_to]
                + "\n\n... (truncated output, please use a smaller directory or apply a filter)"
            )

        return concatenated_output


if __name__ == "__main__":
    print(
        SummarizeAllCodeInPath(
            start_path="./data/agency_data",
            file_extensions=[".py"],
            exclude_directories=["__pycache__", ".git", ".idea", "venv", ".vscode", "node_modules", "build", "dist"],
        ).run(api_key=os.getenv("OPENAI_API_KEY"))
    )
