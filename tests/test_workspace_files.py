import pytest

from security.workspace_files import WorkspaceFileManager
from security.workspace_guard import WorkspaceGuard


def create_file_manager(tmp_path):
    """
    Create a WorkspaceFileManager using a temporary
    workspace root for testing.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    file_manager = WorkspaceFileManager(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    return file_manager


def test_write_file(tmp_path):
    """
    Verify that a Worker can create a file inside
    its workspace.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_path = file_manager.write_file(
        "output/result.txt",
        "Hello Worker",
    )

    assert file_path.exists()
    assert file_path.is_file()
    assert file_path.read_text(
        encoding="utf-8"
    ) == "Hello Worker"


def test_read_file(tmp_path):
    """
    Verify that a Worker can read a file from
    its workspace.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_manager.write_file(
        "output/result.txt",
        "Hello Worker",
    )

    content = file_manager.read_file(
        "output/result.txt"
    )

    assert content == "Hello Worker"


def test_nested_directories_are_supported(tmp_path):
    """
    Verify that nested output directories can be
    created safely.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_manager.write_file(
        "reports/engineering/final/report.txt",
        "Engineering report",
    )

    assert (
        "reports/engineering/final/report.txt"
        in file_manager.list_files()
    )


def test_changed_files_are_tracked(tmp_path):
    """
    Verify that files written by the Worker are
    tracked as changed files.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_manager.write_file(
        "result.txt",
        "Result",
    )

    file_manager.write_file(
        "report.txt",
        "Report",
    )

    changed_files = (
        file_manager.get_changed_files()
    )

    assert changed_files == [
        "result.txt",
        "report.txt",
    ]


def test_duplicate_writes_are_not_duplicated(
    tmp_path,
):
    """
    Verify that writing the same file multiple times
    does not create duplicate entries in the
    changed-files list.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_manager.write_file(
        "result.txt",
        "First version",
    )

    file_manager.write_file(
        "result.txt",
        "Second version",
    )

    assert (
        file_manager.get_changed_files()
        == ["result.txt"]
    )


def test_list_files(tmp_path):
    """
    Verify that list_files() returns all files
    relative to the Worker workspace.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    file_manager.write_file(
        "a.txt",
        "A",
    )

    file_manager.write_file(
        "nested/b.txt",
        "B",
    )

    files = file_manager.list_files()

    assert files == [
        "a.txt",
        "nested/b.txt",
    ]


def test_path_escape_is_blocked(tmp_path):
    """
    Verify that a Worker cannot write outside
    its workspace.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    with pytest.raises(ValueError):

        file_manager.write_file(
            "../worker_002/secret.txt",
            "secret",
        )


def test_read_path_escape_is_blocked(tmp_path):
    """
    Verify that a Worker cannot read outside
    its workspace.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    with pytest.raises(ValueError):

        file_manager.read_file(
            "../../secret.txt"
        )


def test_missing_file_raises_error(tmp_path):
    """
    Verify that reading a non-existent file raises
    FileNotFoundError.
    """

    file_manager = create_file_manager(
        tmp_path
    )

    with pytest.raises(FileNotFoundError):

        file_manager.read_file(
            "missing.txt"
        )