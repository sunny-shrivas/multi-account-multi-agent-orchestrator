from account.account_manager import AccountManager
from models.schemas import Task
from orchestrator.master import MasterOrchestrator


def test_master_executes_account_manager_worker():
    """
    Verify the complete Master execution path:

        Project Plan
            ↓
        Master
            ↓
        Scheduler
            ↓
        AccountManager
            ↓
        Worker
            ↓
        Verification Gate
            ↓
        Completed Task

    Mock Workers are used so no real API calls occur.
    """

    account_manager = AccountManager()

    account_manager.load_from_config(
        "config/workers.test.yaml"
    )

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    task = Task(
        task_id="master_integration_task",
        description="Complete a master integration task",
        acceptance_criteria=[
            "Complete a master integration task",
        ],
    )

    master.load_plan(
        [task]
    )

    results = master.execute_plan()

    assert len(results) == 1

    result = results[0]

    assert (
        result.task_id
        == "master_integration_task"
    )

    assert result.status == "completed"

    assert result.worker_id in {
        "mock_001",
        "mock_002",
        "mock_003",
    }

    assert (
        master.verification_results[
            "master_integration_task"
        ]
        is True
    )

    progress = master.get_progress()

    assert progress["total_tasks"] == 1

    assert progress["completed_tasks"] == 1

    assert progress["verified_tasks"] == 1

    assert progress["failed_tasks"] == 0