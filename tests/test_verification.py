from pathlib import Path

from models.schemas import Task, WorkerResult
from verification.verifier import VerificationGate


def test_verification_passes_for_valid_artifact(tmp_path, monkeypatch):
    """
    A completed Worker with a real artifact satisfying
    all acceptance criteria should pass verification.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    workspace.mkdir(
        parents=True
    )

    artifact = (
        workspace
        / "output"
        / "result.md"
    )

    artifact.parent.mkdir(
        parents=True
    )

    artifact.write_text(
        "Python implementation completed.\n"
        "Unit tests passed.\n",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Implement the feature.",
        acceptance_criteria=[
            "Python implementation completed.",
            "Unit tests passed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.md"
        ],
        notes="Worker completed the task.",
    )

    verifier = VerificationGate()

    assert verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_failed_worker(tmp_path, monkeypatch):
    """
    A WorkerResult with status=failed must never pass
    verification.
    """

    monkeypatch.chdir(tmp_path)

    task = Task(
        task_id="task_001",
        description="Implement the feature.",
        acceptance_criteria=[
            "Implementation completed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="failed",
        files_changed=[],
        notes="Worker crashed.",
        error="Worker crashed.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_result_without_files(
    tmp_path,
    monkeypatch,
):
    """
    A completed Worker must report at least one
    changed file.
    """

    monkeypatch.chdir(tmp_path)

    task = Task(
        task_id="task_001",
        description="Implement the feature.",
        acceptance_criteria=[
            "Implementation completed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[],
        notes="I completed the task.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_missing_artifact(
    tmp_path,
    monkeypatch,
):
    """
    A Worker cannot claim a file was changed if the
    artifact does not actually exist.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    workspace.mkdir(
        parents=True
    )

    task = Task(
        task_id="task_001",
        description="Create an artifact.",
        acceptance_criteria=[
            "Artifact completed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.md"
        ],
        notes="Artifact created.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_empty_artifact(
    tmp_path,
    monkeypatch,
):
    """
    Empty artifacts must not pass verification.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    artifact = (
        workspace
        / "output"
        / "result.md"
    )

    artifact.parent.mkdir(
        parents=True
    )

    artifact.write_text(
        "",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Create an artifact.",
        acceptance_criteria=[
            "Artifact completed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.md"
        ],
        notes="Artifact created.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_missing_acceptance_criterion(
    tmp_path,
    monkeypatch,
):
    """
    Every acceptance criterion must be present in the
    actual artifact content.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    artifact = (
        workspace
        / "output"
        / "result.md"
    )

    artifact.parent.mkdir(
        parents=True
    )

    artifact.write_text(
        "Implementation completed.\n",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Implement the feature.",
        acceptance_criteria=[
            "Implementation completed.",
            "Unit tests passed.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.md"
        ],
        notes="Worker claims everything passed.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_rejects_workspace_escape(
    tmp_path,
    monkeypatch,
):
    """
    A Worker must not be able to report an artifact
    outside its isolated workspace.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    workspace.mkdir(
        parents=True
    )

    outside_file = (
        tmp_path
        / "secret.txt"
    )

    outside_file.write_text(
        "secret data",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Create an artifact.",
        acceptance_criteria=[
            "secret data",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "../../secret.txt"
        ],
        notes="Artifact created.",
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )


def test_verification_accepts_task_without_criteria(
    tmp_path,
    monkeypatch,
):
    """
    If a task has no explicit acceptance criteria,
    a valid non-empty artifact is sufficient for the
    current deterministic verifier.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    artifact = (
        workspace
        / "output"
        / "result.txt"
    )

    artifact.parent.mkdir(
        parents=True
    )

    artifact.write_text(
        "Valid deliverable.",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Create a deliverable.",
        acceptance_criteria=[],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.txt"
        ],
        notes="Completed.",
    )

    verifier = VerificationGate()

    assert verifier.verify(
        task=task,
        result=result,
    )


def test_verification_uses_actual_artifact_not_worker_notes(
    tmp_path,
    monkeypatch,
):
    """
    Verification must inspect the actual artifact rather
    than trusting the WorkerResult notes.
    """

    monkeypatch.chdir(tmp_path)

    workspace = (
        tmp_path
        / "workspaces"
        / "worker_001"
    )

    artifact = (
        workspace
        / "output"
        / "result.md"
    )

    artifact.parent.mkdir(
        parents=True
    )

    artifact.write_text(
        "Actual artifact content is incomplete.",
        encoding="utf-8",
    )

    task = Task(
        task_id="task_001",
        description="Implement the feature.",
        acceptance_criteria=[
            "Feature fully implemented.",
        ],
    )

    result = WorkerResult(
        task_id="task_001",
        worker_id="worker_001",
        status="completed",
        files_changed=[
            "output/result.md"
        ],
        notes=(
            "Feature fully implemented. "
            "All acceptance criteria satisfied."
        ),
    )

    verifier = VerificationGate()

    assert not verifier.verify(
        task=task,
        result=result,
    )