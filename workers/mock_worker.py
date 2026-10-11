from models.schemas import Task, WorkerResult
from workers.base_worker import BaseWorker


class MockWorker(BaseWorker):
    """
    Generic Mock Worker used by the AccountManager
    and configuration-based tests.

    This Worker creates a simple deliverable inside
    its isolated workspace.

    Unlike SuccessMockWorker, this Worker does not attempt
    to satisfy the task's acceptance criteria.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Execute the task and create a basic deliverable.
        """

        self.file_manager.reset_changed_files()

        output_path = "output/result.txt"

        content = (
            f"Worker: {self.worker_id}\n"
            f"Task ID: {task.task_id}\n"
            f"Task: {task.description}\n"
            "Status: completed\n"
        )

        try:
            self.write_file(
                relative_path=output_path,
                content=content,
            )

            changed_files = self.get_changed_files()

            print(
                f"{self.worker_id} COMPLETED "
                f"{task.task_id}"
            )

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                status="completed",
                files_changed=changed_files,
                notes=(
                    f"MockWorker {self.worker_id} "
                    f"completed task: {task.description}"
                ),
                error=None,
            )

        except Exception as exc:
            print(
                f"{self.worker_id} FAILED "
                f"{task.task_id}"
            )

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                status="failed",
                files_changed=[],
                notes=(
                    f"MockWorker {self.worker_id} "
                    "failed to create the deliverable."
                ),
                error=(
                    f"File operation failed: "
                    f"{type(exc).__name__}"
                ),
            )