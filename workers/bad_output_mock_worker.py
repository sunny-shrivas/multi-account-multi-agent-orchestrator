from models.schemas import Task, WorkerResult
from workers.base_worker import BaseWorker


class BadOutputMockWorker(BaseWorker):
    """
    Mock Worker that claims to complete a task but produces
    an invalid deliverable.

    This simulates a Worker returning a successful status
    while failing the actual acceptance criteria.

    The Verification Gate should reject this output, after
    which the Master can reassign the task to another Worker.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Produce an intentionally invalid deliverable.

        The Worker reports status='completed', but the artifact
        does not contain the task's acceptance criteria.
        """

        self.file_manager.reset_changed_files()

        output_path = f"output/{task.task_id}_result.txt"

        content = (
            "INVALID TASK DELIVERABLE\n"
            "========================\n\n"
            f"Worker: {self.worker_id}\n"
            f"Task ID: {task.task_id}\n\n"
            "This Worker intentionally produced an invalid "
            "deliverable for verification testing.\n"
        )

        try:
            self.write_file(
                relative_path=output_path,
                content=content,
            )

            changed_files = self.get_changed_files()

            print(
                f"{self.worker_id} PRODUCED BAD OUTPUT "
                f"for {task.task_id}"
            )

            return WorkerResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                status="completed",
                files_changed=changed_files,
                notes=(
                    f"{self.worker_id} reported completion, "
                    "but the deliverable intentionally does "
                    "not satisfy the acceptance criteria."
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
                    f"{self.worker_id} failed to create "
                    "the invalid test deliverable."
                ),
                error=(
                    f"File operation failed: "
                    f"{type(exc).__name__}"
                ),
            )