import time

from account.account_manager import AccountManager
from models.schemas import Task, WorkerResult
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from workers.base_worker import BaseWorker


class SlowMockWorker(BaseWorker):
    """
    Mock Worker that sleeps during execution.

    Used to verify that independent tasks are
    executed in parallel by the Scheduler.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        print(
            f"{self.worker_id} STARTED {task.task_id}"
        )

        time.sleep(2)

        print(
            f"{self.worker_id} FINISHED {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="completed",
            files_changed=[],
            notes=(
                f"{self.worker_id} completed "
                f"{task.task_id}."
            ),
            error=None,
        )


def test_parallel_execution():
    """
    Verify that independent tasks are executed
    in parallel rather than serially.
    """

    account_manager = AccountManager()

    account_manager.register_worker(
        SlowMockWorker("worker_001")
    )

    account_manager.register_worker(
        SlowMockWorker("worker_002")
    )

    account_manager.register_worker(
        SlowMockWorker("worker_003")
    )

    tasks = [
        Task(
            task_id="task_001",
            description="Task 1",
        ),
        Task(
            task_id="task_002",
            description="Task 2",
        ),
        Task(
            task_id="task_003",
            description="Task 3",
        ),
    ]

    dependency_graph = TaskDependencyGraph()

    dependency_graph.add_tasks(tasks)

    dependency_graph.validate()

    scheduler = Scheduler(
        dependency_graph=dependency_graph,
        account_manager=account_manager,
    )

    start_time = time.time()

    results = scheduler.run()

    elapsed_time = time.time() - start_time

    assert len(results) == 3

    assert all(
        result.status == "completed"
        for result in results
    )

    assert elapsed_time < 5

    print(
        f"\nTotal execution time: "
        f"{elapsed_time:.2f} seconds"
    )


if __name__ == "__main__":
    test_parallel_execution()