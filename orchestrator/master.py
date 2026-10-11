from models.schemas import Task, WorkerResult
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from account.account_manager import AccountManager
from verification.verifier import VerificationGate
from security.run_logger import RunLogger


class MasterOrchestrator:
    """
    Master Orchestrator for the multi-agent system.

    Responsibilities:
    - Accept a project plan represented as Tasks
    - Build and validate the dependency graph
    - Coordinate the Scheduler
    - Receive Worker results
    - Verify Worker results against acceptance criteria
    - Decide whether a task is truly complete
    - Reject invalid Worker output
    - Retry rejected work using another Worker
    - Release dependent tasks only after verification
    - Track execution and verification results
    - Record orchestration events in the run log
    - Report overall progress

    Architectural principle:

        Worker completion != Task completion

    A Worker can report that it completed a task, but the
    Master is the final authority. A task becomes completed
    only after the Verification Gate approves its result.
    """

    def __init__(
        self,
        account_manager: AccountManager,
        run_logger: RunLogger | None = None,
    ):
        self.account_manager = account_manager

        self.dependency_graph = TaskDependencyGraph()

        self.scheduler = Scheduler(
            dependency_graph=self.dependency_graph,
            account_manager=self.account_manager,
        )

        self.verifier = VerificationGate()

        self.run_logger = run_logger or RunLogger()

        self.tasks: list[Task] = []

        self.results: list[WorkerResult] = []

        self.verification_results: dict[str, bool] = {}

        self.verification_retry_count: dict[str, int] = {}

    def load_plan(self, tasks: list[Task]) -> None:
        """
        Load and validate a project plan.

        The dependency graph is rebuilt whenever a new plan
        is loaded.
        """

        self.tasks = tasks

        self.dependency_graph = TaskDependencyGraph()

        self.dependency_graph.add_tasks(tasks)

        self.dependency_graph.validate()

        self.scheduler = Scheduler(
            dependency_graph=self.dependency_graph,
            account_manager=self.account_manager,
        )

        self.results = []

        self.verification_results = {}

        self.verification_retry_count = {}

        self.run_logger.log_event(
            event="PLAN_LOADED",
            details={
                "task_count": len(tasks),
            },
        )

    def execute_plan(self) -> list[WorkerResult]:
        """
        Execute the loaded project plan.

        The Master controls the execution lifecycle.

        For every execution cycle:

            1. Scheduler finds ready tasks.
            2. Workers execute those tasks.
            3. Master receives Worker results.
            4. Master verifies the results.
            5. Only verified tasks are marked completed.
            6. Only then can dependent tasks become ready.

        This creates a true Master-controlled
        Verification Gate.
        """

        if not self.tasks:
            raise ValueError(
                "No project plan has been loaded."
            )

        self.run_logger.log_event(
            event="EXECUTION_STARTED",
            details={
                "task_count": len(self.tasks),
            },
        )

        while True:

            execution_results = (
                self.scheduler.execute_ready_tasks()
            )

            if not execution_results:
                break

            progress_made = False

            for task, result in execution_results:

                self.results.append(result)

                verified = self._process_result(
                    task=task,
                    result=result,
                )

                if verified:
                    progress_made = True

            if not progress_made:

                has_pending_tasks = any(
                    task.status == "pending"
                    and task.task_id
                    not in self.scheduler.completed_tasks
                    for task in self.tasks
                )

                if has_pending_tasks:
                    print(
                        "Execution stopped because "
                        "no task could be verified."
                    )

                break

        self.run_logger.log_event(
            event="EXECUTION_FINISHED",
            details={
                "completed_tasks": len(
                    self.scheduler.completed_tasks
                ),
                "failed_tasks": len(
                    self.scheduler.failed_tasks
                ),
            },
        )

        return self.results

    def _process_result(
        self,
        task: Task,
        result: WorkerResult,
    ) -> bool:
        """
        Process one Worker result through the Master
        verification gate.
        """

        # Record which Worker handled the task.
        #
        # The current Scheduler performs the actual assignment
        # internally. At this layer the Master records the
        # assignment when the result reaches the Master.
        self.run_logger.log_event(
            event="TASK_ASSIGNED",
            task_id=task.task_id,
            worker_id=result.worker_id,
        )

        if result.status == "completed":

            self.run_logger.log_event(
                event="WORKER_COMPLETED",
                task_id=task.task_id,
                worker_id=result.worker_id,
                details={
                    "status": result.status,
                },
            )

        else:

            self.run_logger.log_event(
                event="WORKER_FAILED",
                task_id=task.task_id,
                worker_id=result.worker_id,
                details={
                    "status": result.status,
                    "error": result.error,
                },
            )

        verification_passed = self.verifier.verify(
            task=task,
            result=result,
        )

        self.verification_results[
            task.task_id
        ] = verification_passed

        self.run_logger.log_event(
            event=(
                "VERIFICATION_PASSED"
                if verification_passed
                else "VERIFICATION_FAILED"
            ),
            task_id=task.task_id,
            worker_id=result.worker_id,
        )

        print(
            f"Verification for {task.task_id}: "
            f"{'PASS' if verification_passed else 'FAIL'}"
        )

        if verification_passed:

            self.scheduler.mark_task_verified(
                task.task_id
            )

            return True

        return self._retry_rejected_task(
            task=task,
            rejected_worker_id=result.worker_id,
        )

    def _retry_rejected_task(
        self,
        task: Task,
        rejected_worker_id: str | None = None,
    ) -> bool:
        """
        Retry a task rejected by the Verification Gate.

        The Worker that produced the rejected output is
        excluded from the reassignment.
        """

        retry_count = (
            self.verification_retry_count.get(
                task.task_id,
                0,
            )
        )

        if retry_count >= self.scheduler.max_retries:

            print(
                f"Verification retries exhausted "
                f"for {task.task_id}."
            )

            self.scheduler.mark_task_failed(
                task.task_id
            )

            self.verification_results[
                task.task_id
            ] = False

            self.run_logger.log_event(
                event="TASK_FAILED",
                task_id=task.task_id,
                worker_id=rejected_worker_id,
                details={
                    "reason": "verification_retries_exhausted",
                },
            )

            return False

        self.verification_retry_count[
            task.task_id
        ] = retry_count + 1

        print(
            f"Verification rejected {task.task_id}. "
            f"Requesting retry "
            f"(attempt {retry_count + 1})."
        )

        self.run_logger.log_event(
            event="TASK_REASSIGNED",
            task_id=task.task_id,
            details={
                "attempt": retry_count + 1,
                "excluded_worker": rejected_worker_id,
            },
        )

        retry_result = self.scheduler.retry_task(
            task=task,
            excluded_worker_id=rejected_worker_id,
        )

        if retry_result is None:

            print(
                f"No alternative Worker available "
                f"for verification retry of "
                f"{task.task_id}."
            )

            self.scheduler.mark_task_failed(
                task.task_id
            )

            self.verification_results[
                task.task_id
            ] = False

            self.run_logger.log_event(
                event="TASK_FAILED",
                task_id=task.task_id,
                details={
                    "reason": "no_alternative_worker",
                },
            )

            return False

        self.results.append(retry_result)

        if retry_result.status == "completed":

            self.run_logger.log_event(
                event="WORKER_COMPLETED",
                task_id=task.task_id,
                worker_id=retry_result.worker_id,
                details={
                    "retry": True,
                },
            )

        else:

            self.run_logger.log_event(
                event="WORKER_FAILED",
                task_id=task.task_id,
                worker_id=retry_result.worker_id,
                details={
                    "retry": True,
                    "error": retry_result.error,
                },
            )

        retry_passed = self.verifier.verify(
            task=task,
            result=retry_result,
        )

        self.verification_results[
            task.task_id
        ] = retry_passed

        self.run_logger.log_event(
            event=(
                "VERIFICATION_PASSED"
                if retry_passed
                else "VERIFICATION_FAILED"
            ),
            task_id=task.task_id,
            worker_id=retry_result.worker_id,
            details={
                "retry": True,
            },
        )

        print(
            f"Verification retry for {task.task_id}: "
            f"{'PASS' if retry_passed else 'FAIL'}"
        )

        if retry_passed:

            self.scheduler.mark_task_verified(
                task.task_id
            )

            return True

        self.scheduler.mark_task_failed(
            task.task_id
        )

        self.run_logger.log_event(
            event="TASK_FAILED",
            task_id=task.task_id,
            worker_id=retry_result.worker_id,
            details={
                "reason": "retry_verification_failed",
            },
        )

        return False

    def _get_latest_worker_id(
        self,
        task_id: str,
    ) -> str | None:
        """
        Return the Worker associated with the latest
        result for a task.
        """

        for result in reversed(self.results):

            if result.task_id == task_id:
                return result.worker_id

        return None

    def get_progress(self) -> dict:
        """
        Return the current execution and verification
        progress.
        """

        total_tasks = len(self.tasks)

        completed_tasks = sum(
            1
            for task in self.tasks
            if task.task_id
            in self.scheduler.completed_tasks
        )

        failed_tasks = sum(
            1
            for task in self.tasks
            if task.task_id
            in self.scheduler.failed_tasks
        )

        verified_tasks = sum(
            1
            for passed in self.verification_results.values()
            if passed
        )

        rejected_tasks = sum(
            1
            for passed in self.verification_results.values()
            if not passed
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "verified_tasks": verified_tasks,
            "rejected_tasks": rejected_tasks,
            "remaining_tasks": (
                total_tasks
                - completed_tasks
                - failed_tasks
            ),
        }