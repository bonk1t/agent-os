from pathlib import Path

from backend.custom_skills.BuildDirectoryTree import BuildDirectoryTree


def test_build_directory_tree_with_py_extension(temp_dir):
    """
    Test if BuildDirectoryTree correctly lists only .py files in the directory tree.
    Sorted output without indentation is expected.
    """
    bdt = BuildDirectoryTree(start_directory=temp_dir, file_extensions=[".py"], exclude_directories=["__pycache__"])
    expected_output = "\n".join(sorted(["/sub/test.py", "/sub", ""]))
    assert bdt.run() == expected_output


def test_build_directory_tree_with_multiple_extensions(temp_dir):
    """
    Test if BuildDirectoryTree lists files with multiple specified extensions.
    Sorted output without indentation is expected.
    """
    bdt = BuildDirectoryTree(
        start_directory=temp_dir, file_extensions=[".py", ".txt"], exclude_directories=["__pycache__"]
    )
    expected_output = "\n".join(sorted(["/sub/test.py", "/sub/test.txt", "/sub", ""]))
    actual_output = bdt.run()
    assert actual_output == expected_output


def test_build_directory_tree_default_settings():
    """
    Test if BuildDirectoryTree uses the correct default settings.
    """
    bdt = BuildDirectoryTree()
    assert bdt.start_directory == Path.cwd()
    assert bdt.file_extensions == []
    assert bdt.exclude_directories == []


def test_build_directory_tree_output_length_limit(temp_dir):
    """
    Test if BuildDirectoryTree correctly limits the output length to 3000 characters.
    """
    # Create a large number of files to exceed the limit
    for i in range(180):
        (temp_dir / f"file_{i}.txt").write_text("Dummy content")
    bdt = BuildDirectoryTree(start_directory=temp_dir, exclude_directories=["__pycache__"])
    output = bdt.run()
    assert len(output) <= 3000  # Adjusted to match the MAX_LENGTH constant


def test_build_directory_tree_exclude_directories(temp_dir):
    """
    Test if BuildDirectoryTree correctly excludes specified directories.
    """
    # Create a directory to be excluded
    excluded_dir = temp_dir / "excluded_dir"
    excluded_dir.mkdir()
    (excluded_dir / "excluded_file.txt").write_text("Excluded content")

    bdt = BuildDirectoryTree(start_directory=temp_dir, exclude_directories=["excluded_dir"])
    output = bdt.run()
    assert "excluded_dir" not in output
