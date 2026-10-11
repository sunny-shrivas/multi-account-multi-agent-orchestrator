from account.account_manager import AccountManager
from models.schemas import Task, WorkerResult
from orchestrator.master import MasterOrchestrator
from workers.success_mock_worker import SuccessMockWorker


class BadOutputWorker(SuccessMockWorker):
    """
    Worker that claims to have completed the task,
    but intentionally produces output that does not
    satisfy the acceptance criteria.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Create a real artifact, but make sure the artifact
        does not satisfy the acceptance criteria.
        """

        self.file_manager.reset_changed_files()

        output_path = "output/result.txt"

        content = (
            "This is intentionally invalid output.\n"
            "The requested requirements were not implemented.\n"
        )

        self.write_file(
            relative_path=output_path,
            content=content,
        )

        changed_files = self.get_changed_files()

        print(
            f"{self.worker_id} COMPLETED {task.task_id}"
        )

        return WorkerResult(
            task_id=task.task_id,
            worker_id=self.worker_id,
            status="completed",
            files_changed=changed_files,
            notes=(
                "This output does not satisfy "
                "the requirements."
            ),
            error=None,
        )


class GoodOutputWorker(SuccessMockWorker):
    """
    Worker that produces output satisfying all
    acceptance criteria.
    """

    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Create a real artifact containing every
        acceptance criterion.
        """

        self.file_manager.reset_changed_files()

        output_path = "output/result.txt"

        content = (
            "Task Deliverable\n"
            f"Task: {task.description}\n\n"
            "Implementation details:\n"
        )

        for criterion in task.acceptance_criteria:
            content += f"- {criterion}\n"

        self.write_file(
            relative_path=output_path,
            content=content,
        )

        changed_files = self.get_changed_files()

        print(
            f"{self.worker_id} COMPLETED {task.task_id}"
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


def test_master_rejects_bad_worker_output():
    """
    Verify that the Master rejects invalid Worker output
    and reassigns the task to another Worker.
    """

    account_manager = AccountManager()

    # Register the bad Worker first so it receives
    # the initial assignment.
    account_manager.register_worker(
        BadOutputWorker("worker_bad")
    )

    # Register a second Worker that can successfully
    # complete the task after rejection.
    account_manager.register_worker(
        GoodOutputWorker("worker_good")
    )

    tasks = [
        Task(
            task_id="task_001",
            description="Design a REST API",
            acceptance_criteria=[
                "Define API endpoints",
                "Describe error handling",
            ],
        )
    ]

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    master.load_plan(tasks)

    results = master.execute_plan()

    # There should be two attempts:
    # 1. Bad Worker
    # 2. Good Worker
    assert len(results) == 2

    first_result = results[0]
    second_result = results[1]

    # First Worker completed technically,
    # but its artifact should fail verification.
    assert first_result.worker_id == "worker_bad"

    assert first_result.status == "completed"

    assert first_result.files_changed == [
        "output/result.txt"
    ]

    # The first attempt must have been rejected.
    #
    # The final verification result is True because
    # the second Worker eventually passed. Therefore
    # we verify the rejection through the orchestration
    # run log.
    events = master.run_logger.read_events()

    verification_failures = [
        event
        for event in events
        if event["event"] == "VERIFICATION_FAILED"
        and event["task_id"] == "task_001"
    ]

    assert len(verification_failures) >= 1

    # The Master should reassign the task.
    reassignment_events = [
        event
        for event in events
        if event["event"] == "TASK_REASSIGNED"
        and event["task_id"] == "task_001"
    ]

    assert len(reassignment_events) >= 1

    # Second Worker should be used after rejection.
    assert second_result.worker_id == "worker_good"

    assert second_result.status == "completed"

    assert second_result.files_changed == [
        "output/result.txt"
    ]

    # Final verification should pass.
    assert (
        master.verification_results["task_001"]
        is True
    )

    # The task should have crossed the Master-controlled
    # completion boundary.
    assert (
        "task_001"
        in master.scheduler.completed_tasks
    )

    print("\nFirst Worker result:")
    print(first_result)

    print("\nSecond Worker result:")
    print(second_result)

    print("\nFinal Master verification:")
    print(
        master.verification_results["task_001"]
    )


if __name__ == "__main__":
    test_master_rejects_bad_worker_output()