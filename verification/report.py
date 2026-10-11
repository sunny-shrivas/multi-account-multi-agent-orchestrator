from models.schemas import Task, WorkerResult


class DeliveryReport:
    """
    Generates a plan-vs-delivered report for the Master
    Orchestrator.

    The report compares:

    - Tasks planned
    - Worker results
    - Verification status
    - Final delivery status
    - Final Worker used
    - Number of execution attempts

    For retried tasks, the final Worker result is used as
    the delivered result while the attempt count records
    how many Workers were involved.
    """

    def __init__(
        self,
        tasks: list[Task],
        results: list[WorkerResult],
        verification_results: dict[str, bool],
    ):
        self.tasks = tasks
        self.results = results
        self.verification_results = verification_results

    def generate(self) -> dict:
        """
        Generate a structured plan-vs-delivered report.
        """

        # Keep all attempts for each task.
        task_attempts: dict[str, list[WorkerResult]] = {}

        for result in self.results:
            task_attempts.setdefault(
                result.task_id,
                [],
            ).append(result)

        task_reports = []

        completed_count = 0
        failed_count = 0
        blocked_count = 0

        for task in self.tasks:
            attempts = task_attempts.get(
                task.task_id,
                [],
            )

            # The final Worker result represents the final
            # delivery attempt.
            result = (
                attempts[-1]
                if attempts
                else None
            )

            verification_passed = (
                self.verification_results.get(
                    task.task_id,
                    False,
                )
            )

            if result is None:
                status = "blocked"
                blocked_count += 1

            elif (
                result.status == "completed"
                and verification_passed
            ):
                status = "completed"
                completed_count += 1

            else:
                status = "failed"
                failed_count += 1

            task_reports.append(
                {
                    "task_id": task.task_id,
                    "description": task.description,
                    "planned": True,
                    "worker_id": (
                        result.worker_id
                        if result
                        else None
                    ),
                    "attempt_count": len(attempts),
                    "worker_status": (
                        result.status
                        if result
                        else "not_executed"
                    ),
                    "verification_passed": (
                        verification_passed
                    ),
                    "final_status": status,
                    "files_changed": (
                        result.files_changed
                        if result
                        else []
                    ),
                    "notes": (
                        result.notes
                        if result
                        else ""
                    ),
                    "error": (
                        result.error
                        if result
                        else None
                    ),
                }
            )

        total_tasks = len(self.tasks)

        if total_tasks == 0:
            overall_status = "NO_TASKS"

        elif completed_count == total_tasks:
            overall_status = "COMPLETED"

        elif completed_count > 0:
            overall_status = "PARTIALLY_COMPLETED"

        else:
            overall_status = "FAILED"

        return {
            "summary": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_count,
                "failed_tasks": failed_count,
                "blocked_tasks": blocked_count,
                "overall_status": overall_status,
            },
            "tasks": task_reports,
        }

    def print_report(self) -> None:
        """
        Print a human-readable version of the report.
        """

        report = self.generate()

        summary = report["summary"]

        print("\n")
        print("=" * 60)
        print("MASTER PLAN VS DELIVERED REPORT")
        print("=" * 60)

        print(
            f"Total Tasks:     "
            f"{summary['total_tasks']}"
        )

        print(
            f"Completed:       "
            f"{summary['completed_tasks']}"
        )

        print(
            f"Failed:          "
            f"{summary['failed_tasks']}"
        )

        print(
            f"Blocked:         "
            f"{summary['blocked_tasks']}"
        )

        print(
            f"Overall Status:  "
            f"{summary['overall_status']}"
        )

        print("\nTASK DETAILS")
        print("-" * 60)

        for task in report["tasks"]:

            print(
                f"{task['task_id']} | "
                f"{task['final_status'].upper()} | "
                f"{task['description']}"
            )

            print(
                f"  Final Worker:   "
                f"{task['worker_id'] or 'N/A'}"
            )

            print(
                f"  Attempts:       "
                f"{task['attempt_count']}"
            )

            print(
                f"  Worker Status:  "
                f"{task['worker_status']}"
            )

            print(
                f"  Verification:   "
                f"{'PASS' if task['verification_passed'] else 'FAIL'}"
            )

            if task["files_changed"]:
                print(
                    f"  Files Changed:  "
                    f"{', '.join(task['files_changed'])}"
                )

            if task["error"]:
                print(
                    f"  Error:          "
                    f"{task['error']}"
                )

            print("-" * 60)

        print("=" * 60)