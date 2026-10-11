from models.schemas import Task
from account.account_manager import AccountManager
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from workers.failing_mock_worker import FailingMockWorker
from workers.success_mock_worker import SuccessMockWorker


def test_worker_failure_and_reassignment():
    """
    Verify that a failed Worker causes the Scheduler to
    retry the task using another available Worker.
    """

    account_manager = AccountManager()

    # Register the failing Worker first so it receives
    # the initial assignment.
    account_manager.register_worker(
        FailingMockWorker("worker_001")
    )

    # Register a healthy Worker that can complete the
    # task after the first Worker fails.
    account_manager.register_worker(
        SuccessMockWorker("worker_002")
    )

    tasks = [
        Task(
            task_id="task_001",
            description="Build authentication service",
        )
    ]

    graph = TaskDependencyGraph()

    graph.add_tasks(tasks)
    graph.validate()

    scheduler = Scheduler(
        dependency_graph=graph,
        account_manager=account_manager,
        max_retries=1,
    )

    results = scheduler.run()

    # The Scheduler should return the successful result
    # after the failed Worker is replaced.
    assert len(results) == 1

    result = results[0]

    assert result.task_id == "task_001"

    assert result.status == "completed"

    # The successful result must come from the second Worker.
    assert result.worker_id == "worker_002"

    # The task must ultimately be marked as completed.
    assert (
        "task_001"
        in scheduler.completed_tasks
    )

    # The task must not remain in the failed set.
    assert (
        "task_001"
        not in scheduler.failed_tasks
    )

    # The Scheduler should have recorded one retry.
    assert (
        scheduler.retry_count["task_001"]
        == 1
    )

    print("\nFinal result:")
    print(result)


if __name__ == "__main__":
    test_worker_failure_and_reassignment()