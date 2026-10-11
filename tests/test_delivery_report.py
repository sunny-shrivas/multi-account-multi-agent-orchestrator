from models.schemas import Task, WorkerResult
from verification.report import DeliveryReport


def test_delivery_report():
    """
    Verify that the DeliveryReport correctly compares
    planned tasks against delivered Worker results.
    """

    tasks = [
        Task(
            task_id="task_001",
            description="Design a REST API",
            acceptance_criteria=[
                "Define API endpoints",
            ],
        ),
        Task(
            task_id="task_002",
            description="Write API documentation",
            acceptance_criteria=[
                "Document API usage",
            ],
        ),
    ]

    results = [
        WorkerResult(
            task_id="task_001",
            worker_id="worker_001",
            status="completed",
            files_changed=[
                "api/design.md",
            ],
            notes="API design completed.",
            error=None,
        ),
        WorkerResult(
            task_id="task_002",
            worker_id="worker_002",
            status="failed",
            files_changed=[],
            notes="Documentation task failed.",
            error="Simulated failure.",
        ),
    ]

    verification_results = {
        "task_001": True,
        "task_002": False,
    }

    report_generator = DeliveryReport(
        tasks=tasks,
        results=results,
        verification_results=verification_results,
    )

    report = report_generator.generate()

    # Summary
    assert report["summary"]["total_tasks"] == 2

    assert (
        report["summary"]["completed_tasks"]
        == 1
    )

    assert (
        report["summary"]["failed_tasks"]
        == 1
    )

    assert (
        report["summary"]["blocked_tasks"]
        == 0
    )

    assert (
        report["summary"]["overall_status"]
        == "PARTIALLY_COMPLETED"
    )

    # Task 001
    task_001 = report["tasks"][0]

    assert task_001["task_id"] == "task_001"

    assert (
        task_001["worker_id"]
        == "worker_001"
    )

    assert task_001["attempt_count"] == 1

    assert (
        task_001["worker_status"]
        == "completed"
    )

    assert (
        task_001["verification_passed"]
        is True
    )

    assert (
        task_001["final_status"]
        == "completed"
    )

    assert (
        task_001["files_changed"]
        == ["api/design.md"]
    )

    # Task 002
    task_002 = report["tasks"][1]

    assert task_002["task_id"] == "task_002"

    assert (
        task_002["worker_id"]
        == "worker_002"
    )

    assert task_002["attempt_count"] == 1

    assert (
        task_002["worker_status"]
        == "failed"
    )

    assert (
        task_002["verification_passed"]
        is False
    )

    assert (
        task_002["final_status"]
        == "failed"
    )

    assert (
        task_002["error"]
        == "Simulated failure."
    )

    print("\nDelivery Report:")
    print(report)


def test_delivery_report_tracks_reassignment():
    """
    Verify that the report tracks multiple Worker attempts
    and identifies the final Worker that delivered the task.
    """

    tasks = [
        Task(
            task_id="task_retry",
            description="Implement authentication",
            acceptance_criteria=[
                "Authentication completed",
            ],
        )
    ]

    results = [
        WorkerResult(
            task_id="task_retry",
            worker_id="worker_failed",
            status="failed",
            files_changed=[],
            notes="Worker failed.",
            error="Worker crashed.",
        ),
        WorkerResult(
            task_id="task_retry",
            worker_id="worker_backup",
            status="completed",
            files_changed=[
                "output/result.md",
            ],
            notes="Authentication completed.",
            error=None,
        ),
    ]

    verification_results = {
        "task_retry": True,
    }

    report_generator = DeliveryReport(
        tasks=tasks,
        results=results,
        verification_results=verification_results,
    )

    report = report_generator.generate()

    task_report = report["tasks"][0]

    assert (
        task_report["worker_id"]
        == "worker_backup"
    )

    assert task_report["attempt_count"] == 2

    assert (
        task_report["worker_status"]
        == "completed"
    )

    assert (
        task_report["verification_passed"]
        is True
    )

    assert (
        task_report["final_status"]
        == "completed"
    )

    assert (
        task_report["files_changed"]
        == ["output/result.md"]
    )

    assert (
        report["summary"]["completed_tasks"]
        == 1
    )

    assert (
        report["summary"]["failed_tasks"]
        == 0
    )


if __name__ == "__main__":
    test_delivery_report()
    test_delivery_report_tracks_reassignment()