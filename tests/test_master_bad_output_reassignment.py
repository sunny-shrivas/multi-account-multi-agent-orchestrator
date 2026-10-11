from pathlib import Path

from account.account_manager import AccountManager
from models.schemas import Task
from orchestrator.master import MasterOrchestrator
from security.run_logger import RunLogger
from workers.bad_output_mock_worker import BadOutputMockWorker
from workers.success_mock_worker import SuccessMockWorker


def test_master_reassigns_task_after_bad_output(
    tmp_path: Path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    account_manager = AccountManager()

    bad_worker = BadOutputMockWorker(
        worker_id="bad_output_worker"
    )

    backup_worker = SuccessMockWorker(
        worker_id="backup_worker"
    )

    account_manager.register_worker(bad_worker)
    account_manager.register_worker(backup_worker)

    run_logger = RunLogger(
        log_path=str(tmp_path / "run.log")
    )

    master = MasterOrchestrator(
        account_manager=account_manager,
        run_logger=run_logger,
    )

    task = Task(
        task_id="task_reassignment",
        description="Create an engineering report.",
        acceptance_criteria=[
            "Engineering report",
            "Risk assessment",
        ],
    )

    master.load_plan([task])

    results = master.execute_plan()

    assert len(results) >= 2

    # The first Worker should have produced a completed
    # result that failed verification.
    first_result = results[0]

    assert (
        first_result.worker_id
        == "bad_output_worker"
    )

    assert first_result.status == "completed"

    # The Master should have reassigned the task
    # to the backup Worker.
    final_result = results[-1]

    assert (
        final_result.worker_id
        == "backup_worker"
    )

    assert final_result.status == "completed"

    # The task must ultimately be verified.
    assert (
        master.verification_results[
            "task_reassignment"
        ]
        is True
    )

    assert (
        "task_reassignment"
        in master.scheduler.completed_tasks
    )

    # Verify that the run log records the rejection
    # and subsequent reassignment.
    events = run_logger.read_events()

    event_names = [
        event["event"]
        for event in events
    ]

    assert "VERIFICATION_FAILED" in event_names
    assert "TASK_REASSIGNED" in event_names
    assert "VERIFICATION_PASSED" in event_names