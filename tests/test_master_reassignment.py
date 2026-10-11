from account.account_manager import AccountManager
from models.schemas import Task, WorkerResult
from orchestrator.master import MasterOrchestrator
from workers.base_worker import BaseWorker


class RejectingWorker(BaseWorker):
    """
    Worker that produces output which intentionally fails
    the Verification Gate.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Create a real artifact, but deliberately make the
        artifact fail the acceptance criteria.
        """

        output_path = "output/result.txt"

        content = (
            "Invalid engineering deliverable.\n"
            "The required acceptance criterion was not completed.\n"
        )

        self.write_file(
            relative_path=output_path,
            content=content,
        )

        changed_files = self.get_changed_files()

        print(
            f"{self.worker_id} produced "
            f"invalid output for {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="completed",
            files_changed=changed_files,
            notes=(
                "This output does not satisfy "
                "the criteria."
            ),
            error=None,
        )


class PassingWorker(BaseWorker):
    """
    Worker that produces output satisfying the
    Verification Gate.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Create a real artifact containing the
        required acceptance criterion.
        """

        output_path = "output/result.txt"

        content = (
            "Engineering Task Deliverable\n"
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
            f"{self.worker_id} produced "
            f"valid output for {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="completed",
            files_changed=changed_files,
            notes=(
                "Required acceptance criterion "
                "has been completed."
            ),
            error=None,
        )


def test_master_rejects_and_reassigns_worker():
    """
    Verify the complete rejection and reassignment flow:

        Worker A
            ↓
        Invalid artifact
            ↓
        Verification FAIL
            ↓
        Worker A excluded
            ↓
        Worker B
            ↓
        Valid artifact
            ↓
        Verification PASS
            ↓
        Task completed
    """

    account_manager = AccountManager()

    rejecting_worker = RejectingWorker(
        worker_id="rejecting_worker"
    )

    passing_worker = PassingWorker(
        worker_id="passing_worker"
    )

    account_manager.register_worker(
        rejecting_worker
    )

    account_manager.register_worker(
        passing_worker
    )

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    task = Task(
        task_id="reassignment_task",
        description="Complete a critical engineering task",
        acceptance_criteria=[
            "Required acceptance criterion "
            "has been completed."
        ],
    )

    master.load_plan(
        [task]
    )

    results = master.execute_plan()

    # Two attempts should occur:
    # 1. Rejecting Worker
    # 2. Passing Worker
    assert len(results) == 2

    first_result = results[0]
    second_result = results[1]

    # First Worker must be the rejecting Worker.
    assert (
        first_result.worker_id
        == "rejecting_worker"
    )

    # Second Worker must be the replacement Worker.
    assert (
        second_result.worker_id
        == "passing_worker"
    )

    # Both Workers technically completed execution.
    assert (
        first_result.status
        == "completed"
    )

    assert (
        second_result.status
        == "completed"
    )

    # Both Workers should have produced real artifacts.
    assert (
        first_result.files_changed
        == ["output/result.txt"]
    )

    assert (
        second_result.files_changed
        == ["output/result.txt"]
    )

    # The first artifact should fail verification,
    # while the second artifact should pass.
    assert (
        master.verification_results[
            "reassignment_task"
        ]
        is True
    )

    # The task must ultimately be marked completed.
    assert (
        "reassignment_task"
        in master.scheduler.completed_tasks
    )

    # The task must not be marked failed.
    assert (
        "reassignment_task"
        not in master.scheduler.failed_tasks
    )

    # Verify Master progress.
    progress = master.get_progress()

    assert progress["total_tasks"] == 1

    assert progress["completed_tasks"] == 1

    assert progress["verified_tasks"] == 1

    assert progress["failed_tasks"] == 0