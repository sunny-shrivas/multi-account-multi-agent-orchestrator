from models.schemas import Task, WorkerResult
from workers.base_worker import BaseWorker


class FailingMockWorker(BaseWorker):
    """
    Mock Worker that intentionally fails.

    Used to test Worker failure and reassignment.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Execute the task and return a failed
        WorkerResult containing the Worker identity.
        """

        print(
            f"{self.worker_id} FAILED {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="failed",
            files_changed=[],
            notes="Intentional failure for testing.",
            error="Simulated Worker failure.",
        )