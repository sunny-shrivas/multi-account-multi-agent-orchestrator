from account.account_manager import AccountManager
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from models.schemas import Task


def test_account_manager_workers_execute_through_scheduler():
    """
    Verify the integration between:

        AccountManager
            ↓
        Scheduler
            ↓
        Worker

    No real API provider is used.
    """

    manager = AccountManager()

    manager.load_from_config(
        "config/workers.test.yaml"
    )

    graph = TaskDependencyGraph()

    task = Task(
        task_id="integration_task",
        description="Complete an integration test",
    )

    graph.add_task(task)

    scheduler = Scheduler(
        dependency_graph=graph,
        account_manager=manager,
    )

    results = scheduler.run()

    assert len(results) == 1

    result = results[0]

    assert result.task_id == "integration_task"

    assert result.status == "completed"

    assert result.worker_id in {
        "mock_001",
        "mock_002",
        "mock_003",
    }

    assert (
        result.worker_id
        not in manager.busy_workers
    )