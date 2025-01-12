from pathlib import Path

from agency_swarm import BaseTool
from pydantic import Field, field_validator

from backend.custom_skills.utils import check_directory_traversal, read_file


class PrintFileContents(BaseTool):
    """Print the contents of a specific file."""

    file_name: Path = Field(..., description="The name of the file to be printed. It can be a relative path.")

    _validate_file_name = field_validator("file_name", mode="after")(check_directory_traversal)

    def run(self) -> str:
        """Returns contents of the specified file."""
        file_path = Path(self.file_name).resolve()

        if file_path.is_file():
            return f"{str(file_path)}:\n```\n{read_file(file_path)}\n```\n"
        else:
            return f"File {self.file_name} not found or is not a file."


if __name__ == "__main__":
    print(
        PrintFileContents(
            file_name="example.txt",
        ).run()
    )
