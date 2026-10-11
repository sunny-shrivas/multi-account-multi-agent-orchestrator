from pathlib import Path

import pytest

from security.workspace_guard import WorkspaceGuard
from workers.mock_worker import MockWorker


def test_worker_workspace_is_created(tmp_path):
    """
    Verify that every Worker receives its own workspace.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    worker = MockWorker(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    expected_workspace = (
        workspace_root / "worker_001"
    ).resolve()

    assert worker.workspace == expected_workspace
    assert worker.workspace.exists()
    assert worker.workspace.is_dir()


def test_worker_can_access_file_inside_workspace(tmp_path):
    """
    Verify that paths inside the Worker's workspace
    are allowed.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    worker = MockWorker(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    validated_path = (
        worker.validate_workspace_path(
            "output/result.txt"
        )
    )

    expected_path = (
        workspace_root
        / "worker_001"
        / "output"
        / "result.txt"
    ).resolve()

    assert validated_path == expected_path


def test_worker_cannot_escape_workspace(tmp_path):
    """
    Verify that path traversal outside the Worker
    workspace is rejected.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    worker = MockWorker(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    with pytest.raises(ValueError):
        worker.validate_workspace_path(
            "../worker_002/secret.txt"
        )


def test_worker_cannot_access_parent_directory(tmp_path):
    """
    Verify that a Worker cannot access files in the
    parent directory of its workspace.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    worker = MockWorker(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    with pytest.raises(ValueError):
        worker.validate_workspace_path(
            "../../secret.txt"
        )


def test_multiple_workers_get_separate_workspaces(tmp_path):
    """
    Verify that different Workers receive isolated
    workspace directories.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    worker_one = MockWorker(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    worker_two = MockWorker(
        worker_id="worker_002",
        workspace_guard=guard,
    )

    assert worker_one.workspace != worker_two.workspace

    assert worker_one.workspace.name == "worker_001"
    assert worker_two.workspace.name == "worker_002"

    assert worker_one.workspace.exists()
    assert worker_two.workspace.exists()


def test_malicious_worker_id_cannot_escape_workspace(tmp_path):
    """
    Verify that a malicious Worker ID cannot cause the
    Worker workspace itself to escape the workspace root.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    with pytest.raises(ValueError):
        guard.create_workspace(
            "../../attacker"
        )