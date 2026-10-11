from models.schemas import Task, WorkerResult
from workers.base_worker import BaseWorker


class SuccessMockWorker(BaseWorker):
    """
    Mock Worker that successfully creates a valid deliverable.

    Used for:

    - Happy-path testing
    - Worker reassignment testing
    - Scheduler testing
    - Multi-account demo execution

    Each task receives its own artifact file so that
    multiple tasks handled by the same Worker cannot
    overwrite each other's deliverables.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Execute the task and create a valid deliverable
        inside the Worker's isolated workspace.
        """

        self.file_manager.reset_changed_files()

        # Every task gets its own artifact.
        output_path = f"output/{task.task_id}_result.txt"

        content = (
            "TASK DELIVERABLE\n"
            "================\n\n"
            f"Worker: {self.worker_id}\n"
            f"Task ID: {task.task_id}\n"
            f"Task: {task.description}\n\n"
            "ACCEPTANCE CRITERIA\n"
            "-------------------\n"
        )

        if task.acceptance_criteria:
            for criterion in task.acceptance_criteria:
                content += f"- {criterion}\n"
        else:
            content += (
                "- No explicit acceptance criteria provided.\n"
            )

        content += (
            "\nIMPLEMENTATION STATUS\n"
            "---------------------\n"
            "The requested task has been completed "
            "by the Mock Worker.\n"
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
                    f"{self.worker_id} successfully "
                    f"completed task {task.task_id}."
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
                    f"{self.worker_id} failed to "
                    "create the deliverable."
                ),
                error=(
                    f"File operation failed: "
                    f"{type(exc).__name__}"
                ),
            )