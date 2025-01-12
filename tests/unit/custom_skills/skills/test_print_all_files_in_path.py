import pytest

from backend.custom_skills.PrintAllFilesInPath import PrintAllFilesInPath


def test_print_all_files_no_extension_filter(temp_dir):
    """
    Test if PrintAllFilesInPath correctly prints contents of all files when no file extension filter is applied.
    """
    pafid = PrintAllFilesInPath(start_path=temp_dir, exclude_directories=["__pycache__"])
    expected_output = {
        f"{temp_dir}/sub/test.py:\n```\nprint('hello')\n```",
        f"{temp_dir}/sub/test.txt:\n```\nhello world\n```",
    }
    actual_output = set(pafid.run().strip().split("\n\n"))
    assert actual_output == expected_output


def test_print_all_files_with_py_extension(temp_dir):
    """
    Test if PrintAllFilesInPath correctly prints contents of .py files only.
    """
    pafid = PrintAllFilesInPath(start_path=temp_dir, file_extensions=[".py"], exclude_directories=["__pycache__"])
    expected_output = f"{temp_dir.joinpath('sub', 'test.py')}:\n```\nprint('hello')\n```\n"
    assert pafid.run() == expected_output


def test_print_all_files_with_txt_extension(temp_dir):
    """
    Test if PrintAllFilesInPath correctly prints contents of .txt files only.
    """
    pafid = PrintAllFilesInPath(start_path=temp_dir, file_extensions=[".txt"], exclude_directories=["__pycache__"])
    expected_output = f"{temp_dir.joinpath('sub', 'test.txt')}:\n```\nhello world\n```\n"
    assert pafid.run() == expected_output


def test_print_all_files_error_reading_file(temp_dir):
    """
    Test if PrintAllFilesInPath handles errors while reading a file.
    """
    # Create an unreadable file
    unreadable_file = temp_dir.joinpath("unreadable_file.txt")
    unreadable_file.write_text("content")
    unreadable_file.chmod(0o000)  # make the file unreadable
    pafid = PrintAllFilesInPath(start_path=temp_dir, file_extensions=[".txt"], exclude_directories=["__pycache__"])
    assert "Error reading file" in pafid.run()
    unreadable_file.chmod(0o644)  # reset file permissions for cleanup


@pytest.mark.parametrize("extension, expected_file", [(".py", "test.py"), (".txt", "test.txt")])
def test_print_all_files_with_extension_filter(temp_dir, extension, expected_file):
    pafip = PrintAllFilesInPath(start_path=temp_dir, file_extensions=[extension], exclude_directories=["__pycache__"])
    expected_output = (
        f"{temp_dir.joinpath('sub', expected_file)}:\n```\n"
        + temp_dir.joinpath("sub", expected_file).read_text()
        + "\n```"
    )
    assert pafip.run().strip() == expected_output.strip()


@pytest.fixture
def create_file_in_path(tmp_path):
    # Create a file and write contents to it
    file_path = tmp_path / "example.txt"
    file_path.write_text("File content")
    return file_path


def test_print_file_contents(create_file_in_path):
    skill = PrintAllFilesInPath(
        start_path=create_file_in_path, file_extensions=[".txt"], exclude_directories=["__pycache__"]
    )
    result = skill.run()
    expected_result = f"{str(create_file_in_path)}:\n```\nFile content\n```\n"
    assert result == expected_result


def test_print_all_files_exclude_directories(temp_dir):
    """
    Test if PrintAllFilesInPath correctly excludes specified directories.
    """
    # Create a directory to be excluded
    excluded_dir = temp_dir / "excluded_dir"
    excluded_dir.mkdir()
    (excluded_dir / "excluded_file.txt").write_text("Excluded content")

    pafid = PrintAllFilesInPath(start_path=temp_dir, exclude_directories=["excluded_dir"])
    output = pafid.run()
    assert "excluded_dir" not in output
