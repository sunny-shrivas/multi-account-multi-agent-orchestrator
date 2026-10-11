from pathlib import Path

from models.schemas import Task
from workers.bad_output_mock_worker import BadOutputMockWorker


def test_bad_output_worker_reports_completed_but_creates_invalid_artifact(
    tmp_path: Path,
):
    worker = BadOutputMockWorker(
        worker_id="bad_output_test_worker"
    )

    task = Task(
        task_id="task_bad_output",
        description="Create a valid engineering report.",
        acceptance_criteria=[
            "Engineering report",
            "Risk assessment",
        ],
    )

    result = worker.execute(task)

    assert result.status == "completed"
    assert result.files_changed

    artifact_path = (
        worker.workspace
        / result.files_changed[0]
    )

    assert artifact_path.exists()

    content = artifact_path.read_text(
        encoding="utf-8"
    )

    # The intentionally bad Worker should NOT include
    # the required acceptance criteria.
    assert "Engineering report" not in content
    assert "Risk assessment" not in content