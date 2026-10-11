from security.workspace_guard import WorkspaceGuard
from workers.mock_worker import MockWorker
from models.schemas import Task


def test_mock_worker_creates_real_artifact(tmp_path):
    """
    Verify that MockWorker creates a real artifact
    inside its isolated workspace and reports the file
    through WorkerResult.files_changed.
    """

    guard = WorkspaceGuard(
        base_directory=str(
            tmp_path / "workspaces"
        )
    )

    worker = MockWorker(
        worker_id="mock_artifact_worker",
        workspace_guard=guard,
    )

    task = Task(
        task_id="artifact_task",
        description="Create a test deliverable",
        acceptance_criteria=[],
    )

    result = worker.execute(task)

    assert result.status == "completed"

    assert (
        "output/result.txt"
        in result.files_changed
    )

    artifact_path = (
        worker.workspace
        / "output"
        / "result.txt"
    )

    assert artifact_path.exists()
    assert artifact_path.is_file()

    content = artifact_path.read_text(
        encoding="utf-8"
    )

    assert "artifact_task" in content
    assert "Create a test deliverable" in content
    assert "completed" in content