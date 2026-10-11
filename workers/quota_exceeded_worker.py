from models.schemas import Task, WorkerResult
from workers.base_worker import BaseWorker


class QuotaExceededWorker(BaseWorker):
    """
    Mock Worker that simulates an AI provider quota
    being exhausted.

    This allows us to test how the Master handles a
    Worker that becomes unavailable because its provider
    quota has been exhausted.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Simulate a provider quota exhaustion failure.
        """

        print(
            f"{self.worker_id} QUOTA EXHAUSTED "
            f"for {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="failed",
            files_changed=[],
            notes=(
                f"Worker {self.worker_id} "
                "could not execute the task because "
                "the provider quota was exhausted."
            ),
            error="QUOTA_EXHAUSTED",
        )