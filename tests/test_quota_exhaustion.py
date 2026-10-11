from account.account_manager import AccountManager
from models.schemas import Task, WorkerResult
from orchestrator.master import MasterOrchestrator
from workers.quota_exceeded_worker import QuotaExceededWorker
from workers.success_mock_worker import SuccessMockWorker


class QuotaBackupWorker(SuccessMockWorker):
    """
    Backup Worker that produces output satisfying the
    task acceptance criteria.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Create a real artifact containing all acceptance
        criteria so the Verification Gate can inspect it.
        """

        output_path = "output/result.txt"

        content = (
            "Authentication Module Deliverable\n"
            f"Task: {task.description}\n\n"
            "Completed Requirements:\n"
        )

        for criterion in task.acceptance_criteria:
            content += f"- {criterion}\n"

        self.write_file(
            relative_path=output_path,
            content=content,
        )

        changed_files = self.get_changed_files()

        print(
            f"{self.worker_id} COMPLETED "
            f"{task.task_id}"
        )

        notes = " ".join(
            task.acceptance_criteria
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="completed",
            files_changed=changed_files,
            notes=notes,
            error=None,
        )


def test_quota_exhaustion_reassigns_task():
    """
    Verify that when a Worker exhausts its provider quota,
    the Master reassigns the task to another Worker and
    verifies the replacement result successfully.
    """

    account_manager = AccountManager()

    account_manager.register_worker(
        QuotaExceededWorker("worker_quota")
    )

    account_manager.register_worker(
        QuotaBackupWorker("worker_backup")
    )

    tasks = [
        Task(
            task_id="task_quota",
            description="Implement authentication module",
            acceptance_criteria=[
                "Authentication module completed",
            ],
        )
    ]

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    master.load_plan(tasks)

    results = master.execute_plan()

    # Two attempts should occur:
    # 1. Quota-exhausted Worker
    # 2. Backup Worker
    assert len(results) == 2

    first_result = results[0]
    second_result = results[1]

    # First Worker must fail because its provider quota
    # has been exhausted.
    assert first_result.worker_id == "worker_quota"

    assert first_result.status == "failed"

    assert first_result.error == "QUOTA_EXHAUSTED"

    # Backup Worker should successfully execute the task.
    assert second_result.worker_id == "worker_backup"

    assert second_result.status == "completed"

    # Backup Worker must have produced a real artifact.
    assert second_result.files_changed == [
        "output/result.txt"
    ]

    # The Master must verify the backup artifact.
    assert (
        master.verification_results["task_quota"]
        is True
    )

    # The task should ultimately be completed.
    assert (
        "task_quota"
        in master.scheduler.completed_tasks
    )

    print("\nQuota Worker Result:")
    print(first_result)

    print("\nBackup Worker Result:")
    print(second_result)

    print("\nFinal Verification:")
    print(
        master.verification_results["task_quota"]
    )


if __name__ == "__main__":
    test_quota_exhaustion_reassigns_task()