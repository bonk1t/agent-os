from collections import deque
from pathlib import Path

from agency_swarm import BaseTool
from pydantic import Field, field_validator

from backend.custom_skills.utils import check_directory_traversal

MAX_LENGTH = 10000


class DirectoryNode:
    """Class to represent a directory node in the tree."""

    def __init__(self, path: Path, level: int):
        self.path = path
        self.level = level
        self.children: list[DirectoryNode | FileNode] = []  # List of DirectoryNode and FileNode


class FileNode:
    """Class to represent a file node in the tree."""

    def __init__(self, path: Path, level: int):
        self.path = path
        self.level = level


class BuildDirectoryTree(BaseTool):
    """Print the structure of directories and files. Directory traversal is not allowed (you cannot read /* or ../*)."""

    start_directory: Path = Field(
        default_factory=Path.cwd,
        description="The starting directory for the tree, defaults to the current working directory.",
    )
    file_extensions: list[str] = Field(
        default_factory=list,
        description="List of file extensions to include in the tree. If empty, all files will be included. "
        "Examples are ['.py', '.txt', '.md'].",
    )
    exclude_directories: list[str] = Field(
        default_factory=list,
        description="List of directories to exclude from the tree. Examples are ['__pycache__', '.git'].",
    )

    _validate_start_directory = field_validator("start_directory", mode="after")(check_directory_traversal)

    def build_tree(self) -> DirectoryNode:
        """Builds the directory tree."""
        root = DirectoryNode(self.start_directory, 0)
        queue = deque([root])

        while queue:
            current_node = queue.popleft()
            children = [p for p in current_node.path.iterdir() if not p.name.startswith(".")]

            for child in children:
                if child.is_dir() and child.name not in self.exclude_directories:
                    dir_node = DirectoryNode(child, current_node.level + 1)
                    current_node.children.append(dir_node)
                    queue.append(dir_node)
                elif child.is_file() and (not self.file_extensions or child.suffix in self.file_extensions):
                    file_node = FileNode(child, current_node.level + 1)
                    current_node.children.append(file_node)

        return root

    def serialize_tree(self, root: DirectoryNode) -> str:
        """Serialize the tree into a string with a character limit."""
        tree_lines = []
        current_length = 0
        message = ""
        cur_dir = str(Path.cwd())
        queue: deque[DirectoryNode | FileNode] = deque([root])

        while queue:
            node = queue.popleft()
            # make sure to remove the prefix (current directory path):
            node_str = f"{node.path}"
            if node_str.startswith(cur_dir):
                node_str = node_str.replace(cur_dir, "")

            if current_length + len(node_str) > MAX_LENGTH:
                message = "\n...\n[truncated output, use a smaller directory or apply a filter on file types]"
                break  # Stop adding more nodes if limit is exceeded

            tree_lines.append(node_str)
            current_length += len(node_str)

            if isinstance(node, DirectoryNode):
                queue.extend(node.children)

        tree_lines.sort()  # Sorting the tree at the end
        return "\n".join(tree_lines) + message

    def run(self) -> str:
        """Build and serialize the directory tree within the character limit."""
        tree_root = self.build_tree()
        return self.serialize_tree(tree_root)


if __name__ == "__main__":
    print(
        BuildDirectoryTree(
            file_extensions=[],
            exclude_directories=["__pycache__", ".git", ".idea", "venv", ".vscode", "node_modules", "build", "dist"],
        ).run()
    )
