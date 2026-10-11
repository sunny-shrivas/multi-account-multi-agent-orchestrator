import time

from account.account_manager import AccountManager
from models.schemas import Task
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from workers.success_mock_worker import SuccessMockWorker


class SlowSuccessWorker(SuccessMockWorker):
    """
    Worker used to prove that independent tasks can execute
    in parallel.
    """

    def execute(self, task):
        time.sleep(0.2)
        return super().execute(task)


def create_scheduler(tasks, workers, max_retries=1):
    """
    Helper that creates a Scheduler with the supplied
    tasks and Workers.
    """

    account_manager = AccountManager()

    for worker in workers:
        account_manager.register_worker(worker)

    graph = TaskDependencyGraph()
    graph.add_tasks(tasks)
    graph.validate()

    return Scheduler(
        dependency_graph=graph,
        account_manager=account_manager,
        max_retries=max_retries,
    )


def test_independent_tasks_execute_in_parallel():
    """
    Independent tasks should be assigned to different Workers
    and executed concurrently.
    """

    tasks = [
        Task(
            task_id="task_001",
            description="Build authentication service",
        ),
        Task(
            task_id="task_002",
            description="Build logging service",
        ),
    ]

    workers = [
        SlowSuccessWorker("worker_001"),
        SlowSuccessWorker("worker_002"),
    ]

    scheduler = create_scheduler(
        tasks=tasks,
        workers=workers,
    )

    start_time = time.perf_counter()

    results = scheduler.run()

    elapsed_time = time.perf_counter() - start_time

    assert len(results) == 2

    assert {
        result.task_id
        for result in results
    } == {
        "task_001",
        "task_002",
    }

    assert all(
        result.status == "completed"
        for result in results
    )

    assert {
        result.worker_id
        for result in results
    } == {
        "worker_001",
        "worker_002",
    }

    # If the two 0.2-second tasks ran sequentially,
    # execution would take roughly 0.4 seconds.
    #
    # Parallel execution should be significantly faster.
    assert elapsed_time < 0.35


def test_dependency_ordering():
    """
    A dependent task must not execute until its dependency
    has completed.
    """

    tasks = [
        Task(
            task_id="task_001",
            description="Create database schema",
        ),
        Task(
            task_id="task_002",
            description="Create API service",
            dependencies=["task_001"],
        ),
    ]

    workers = [
        SuccessMockWorker("worker_001"),
        SuccessMockWorker("worker_002"),
    ]

    scheduler = create_scheduler(
        tasks=tasks,
        workers=workers,
    )

    results = scheduler.run()

    assert len(results) == 2

    assert results[0].task_id == "task_001"
    assert results[1].task_id == "task_002"

    assert results[0].status == "completed"
    assert results[1].status == "completed"

    assert "task_001" in scheduler.completed_tasks
    assert "task_002" in scheduler.completed_tasks


def test_master_verification_controls_completion():
    """
    execute_ready_tasks() must not mark a successful task
    as completed automatically.

    The Master must explicitly call mark_task_verified()
    after the Verification Gate passes.
    """

    task = Task(
        task_id="task_001",
        description="Build authentication service",
    )

    workers = [
        SuccessMockWorker("worker_001"),
    ]

    scheduler = create_scheduler(
        tasks=[task],
        workers=workers,
    )

    results = scheduler.execute_ready_tasks()

    assert len(results) == 1

    returned_task, result = results[0]

    assert returned_task.task_id == "task_001"
    assert result.status == "completed"

    # Worker succeeded, but Master has not verified it yet.
    assert "task_001" not in scheduler.completed_tasks

    # Master now approves the result.
    scheduler.mark_task_verified("task_001")

    assert "task_001" in scheduler.completed_tasks


def test_no_available_worker_returns_no_results():
    """
    If there are no available Workers, the Scheduler should
    safely return without executing the task.
    """

    task = Task(
        task_id="task_001",
        description="Build authentication service",
    )

    scheduler = create_scheduler(
        tasks=[task],
        workers=[],
    )

    results = scheduler.execute_ready_tasks()

    assert results == []

    assert "task_001" not in scheduler.completed_tasks
    assert "task_001" not in scheduler.failed_tasks