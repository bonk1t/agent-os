from pathlib import Path

from agency_swarm import BaseTool
from pydantic import Field, field_validator

from backend.custom_skills.utils import check_directory_traversal, read_file


class PrintAllFilesInPath(BaseTool):
    """Print the contents of all files in a start_path recursively.
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
    exclude_directories: list[str] = Field(
        default_factory=list,
        description="List of directories to exclude from the search. Examples are ['__pycache__', '.git'].",
    )
    truncate_to: int = Field(
        default=None,
        description="Truncate the output to this many characters. If None or skipped, the output is not truncated.",
    )

    _validate_start_path = field_validator("start_path", mode="after")(check_directory_traversal)

    def run(self) -> str:
        """
        Recursively searches for files within `start_path` and compiles their contents into a single string.
        """
        output = []
        start_path = self.start_path.resolve()

        # if start_path is a file, just read it
        if start_path.is_file():
            return f"{str(start_path)}:\n```\n{read_file(start_path)}\n```\n"

        for path in start_path.rglob("*"):
            # ignore files in hidden directories or excluded directories
            if any(part.startswith(".") for part in path.parts) or any(
                part in self.exclude_directories for part in path.parts
            ):
                continue

            if path.is_file() and (not self.file_extensions or path.suffix in self.file_extensions):
                output.append(f"{str(path)}:\n```\n{read_file(path)}\n```\n")

        output_str = "\n".join(output)
        if self.truncate_to and len(output_str) > self.truncate_to:
            output_str = (
                output_str[: self.truncate_to]
                + "\n\n... (truncated output, please use a smaller directory or apply a filter)"
            )

        return output_str


if __name__ == "__main__":
    # list of extensions: ".py", ".json", ".yaml", ".yml", ".md", ".txt", ".tsx", ".ts", ".js", ".jsx", ".html"
    print(
        PrintAllFilesInPath(
            start_path=".",
            # file_extensions=[],
            file_extensions=[".tsx", ".ts"],
            exclude_directories=[
                # "frontend",
                "__pycache__",
                ".git",
                ".idea",
                "venv",
                ".vscode",
                "node_modules",
                "build",
                "dist",
            ],
        ).run()
    )
