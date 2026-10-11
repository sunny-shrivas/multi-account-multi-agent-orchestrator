from security.workspace_files import WorkspaceFileManager
from security.workspace_guard import WorkspaceGuard


def test_changed_files_reset_between_executions(tmp_path):
    """
    Verify that changed-file tracking represents only
    the current Worker execution lifecycle.
    """

    workspace_root = tmp_path / "workspaces"

    guard = WorkspaceGuard(
        base_directory=str(workspace_root)
    )

    manager = WorkspaceFileManager(
        worker_id="worker_001",
        workspace_guard=guard,
    )

    # Simulate the first task execution.
    manager.reset_changed_files()

    manager.write_file(
        relative_path="output/task_1.txt",
        content="Task 1 output",
    )

    assert manager.get_changed_files() == [
        "output/task_1.txt"
    ]

    # Simulate the second task execution.
    manager.reset_changed_files()

    manager.write_file(
        relative_path="output/task_2.txt",
        content="Task 2 output",
    )

    # Task 1's file must not appear in Task 2's
    # changed-file result.
    assert manager.get_changed_files() == [
        "output/task_2.txt"
    ]