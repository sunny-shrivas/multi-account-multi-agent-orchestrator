from pathlib import Path

from models.schemas import Task
from verification.verifier import VerificationGate
from workers.bad_output_mock_worker import BadOutputMockWorker


def test_verification_gate_rejects_bad_worker_output(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    worker = BadOutputMockWorker(
        worker_id="bad_output_verification_worker"
    )

    task = Task(
        task_id="task_verification_rejection",
        description="Create an engineering report.",
        acceptance_criteria=[
            "Engineering report",
            "Risk assessment",
        ],
    )

    result = worker.execute(task)

    verifier = VerificationGate()

    verification_passed = verifier.verify(
        task=task,
        result=result,
    )

    assert result.status == "completed"

    assert verification_passed is False