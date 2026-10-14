from models.schemas import Task, WorkerResult
from orchestrator.dependency_graph import TaskDependencyGraph
from orchestrator.scheduler import Scheduler
from account.account_manager import AccountManager
from verification.verifier import VerificationGate
from security.run_logger import RunLogger
from orchestrator.plan_parser import PlanParser


class MasterOrchestrator:
    """
    Master Orchestrator for the multi-agent system.

    Responsibilities:
    - Accept a project plan as Tasks or natural-language text
    - Decompose written plans into structured Tasks
    - Build and validate the dependency graph
    - Coordinate the Scheduler
    - Receive and verify Worker results
    - Reject invalid output and retry using another Worker
    - Release dependent tasks only after verification
    - Track execution, verification, and progress
    - Record orchestration events
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
        """Load a pre-structured project plan."""
        if not tasks:
            raise ValueError("Project plan must contain at least one task.")

        self._initialize_plan(tasks)

    def load_plan_from_text(
        self,
        project_plan: str,
        *,
        acceptance_criteria: dict[str, list[str]] | None = None,
        dependencies: dict[str, list[str]] | None = None,
    ) -> list[Task]:
        """
        Parse a written plan into Tasks and load it for execution.

        Example:
            tasks = master.load_plan_from_text(
                '''
                1. Design the API
                2. Implement the API
                3. Write tests
                ''',
                dependencies={"task_002": ["task_001"],
                              "task_003": ["task_002"]},
            )

        This is deterministic parsing, not LLM-based planning.
        """
        tasks = PlanParser.parse(
            project_plan,
            acceptance_criteria=acceptance_criteria,
            dependencies=dependencies,
        )
        self._initialize_plan(tasks)
        return tasks

    def _initialize_plan(self, tasks: list[Task]) -> None:
        """Validate and initialize all state for a new plan."""
        task_ids = [task.task_id for task in tasks]

        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Project plan contains duplicate task IDs.")

        known_ids = set(task_ids)

        for task in tasks:
            unknown_dependencies = (
                set(task.dependencies) - known_ids
            )
            if unknown_dependencies:
                raise ValueError(
                    f"Task {task.task_id} references unknown dependencies: "
                    f"{', '.join(sorted(unknown_dependencies))}"
                )

            if task.task_id in task.dependencies:
                raise ValueError(
                    f"Task {task.task_id} cannot depend on itself."
                )

        graph = TaskDependencyGraph()
        graph.add_tasks(tasks)
        graph.validate()

        self.tasks = tasks
        self.dependency_graph = graph
        self.scheduler = Scheduler(
            dependency_graph=self.dependency_graph,
            account_manager=self.account_manager,
        )
        self.results = []
        self.verification_results = {}
        self.verification_retry_count = {}

        self.run_logger.log_event(
            event="PLAN_LOADED",
            details={"task_count": len(tasks)},
        )

    def execute_plan(self) -> list[WorkerResult]:
        """Execute tasks, verifying each result before releasing dependents."""
        if not self.tasks:
            raise ValueError("No project plan has been loaded.")

        self.run_logger.log_event(
            event="EXECUTION_STARTED",
            details={"task_count": len(self.tasks)},
        )

        while True:
            execution_results = self.scheduler.execute_ready_tasks()

            if not execution_results:
                break

            progress_made = False

            for task, result in execution_results:
                self.results.append(result)
                verified = self._process_result(task, result)

                if verified:
                    progress_made = True

            if not progress_made:
                has_pending_tasks = any(
                    task.status == "pending"
                    and task.task_id not in self.scheduler.completed_tasks
                    and task.task_id not in self.scheduler.failed_tasks
                    for task in self.tasks
                )

                if has_pending_tasks:
                    print(
                        "Execution stopped because no task could be verified."
                    )
                break

        self.run_logger.log_event(
            event="EXECUTION_FINISHED",
            details={
                "completed_tasks": len(self.scheduler.completed_tasks),
                "failed_tasks": len(self.scheduler.failed_tasks),
            },
        )

        return self.results

    def _process_result(
        self,
        task: Task,
        result: WorkerResult,
    ) -> bool:
        """Process one Worker result through the verification gate."""
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
                details={"status": result.status},
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
        self.verification_results[task.task_id] = verification_passed

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
            self.scheduler.mark_task_verified(task.task_id)
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
        """Retry rejected output using another Worker when available."""
        retry_count = self.verification_retry_count.get(task.task_id, 0)

        if retry_count >= self.scheduler.max_retries:
            print(f"Verification retries exhausted for {task.task_id}.")
            self.scheduler.mark_task_failed(task.task_id)
            self.verification_results[task.task_id] = False

            self.run_logger.log_event(
                event="TASK_FAILED",
                task_id=task.task_id,
                worker_id=rejected_worker_id,
                details={"reason": "verification_retries_exhausted"},
            )
            return False

        self.verification_retry_count[task.task_id] = retry_count + 1

        print(
            f"Verification rejected {task.task_id}. "
            f"Requesting retry (attempt {retry_count + 1})."
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
                f"No alternative Worker available for "
                f"verification retry of {task.task_id}."
            )
            self.scheduler.mark_task_failed(task.task_id)
            self.verification_results[task.task_id] = False

            self.run_logger.log_event(
                event="TASK_FAILED",
                task_id=task.task_id,
                details={"reason": "no_alternative_worker"},
            )
            return False

        self.results.append(retry_result)

        if retry_result.status == "completed":
            self.run_logger.log_event(
                event="WORKER_COMPLETED",
                task_id=task.task_id,
                worker_id=retry_result.worker_id,
                details={"retry": True},
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
        self.verification_results[task.task_id] = retry_passed

        self.run_logger.log_event(
            event=(
                "VERIFICATION_PASSED"
                if retry_passed
                else "VERIFICATION_FAILED"
            ),
            task_id=task.task_id,
            worker_id=retry_result.worker_id,
            details={"retry": True},
        )

        print(
            f"Verification retry for {task.task_id}: "
            f"{'PASS' if retry_passed else 'FAIL'}"
        )

        if retry_passed:
            self.scheduler.mark_task_verified(task.task_id)
            return True

        self.scheduler.mark_task_failed(task.task_id)

        self.run_logger.log_event(
            event="TASK_FAILED",
            task_id=task.task_id,
            worker_id=retry_result.worker_id,
            details={"reason": "retry_verification_failed"},
        )
        return False

    def _get_latest_worker_id(self, task_id: str) -> str | None:
        """Return the Worker associated with the latest result for a task."""
        for result in reversed(self.results):
            if result.task_id == task_id:
                return result.worker_id
        return None

    def get_progress(self) -> dict:
        """Return current execution and verification progress."""
        total_tasks = len(self.tasks)

        completed_tasks = sum(
            1 for task in self.tasks
            if task.task_id in self.scheduler.completed_tasks
        )
        failed_tasks = sum(
            1 for task in self.tasks
            if task.task_id in self.scheduler.failed_tasks
        )
        verified_tasks = sum(
            1 for passed in self.verification_results.values() if passed
        )
        rejected_tasks = sum(
            1 for passed in self.verification_results.values() if not passed
        )

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "verified_tasks": verified_tasks,
            "rejected_tasks": rejected_tasks,
            "remaining_tasks": total_tasks - completed_tasks - failed_tasks,
        }
