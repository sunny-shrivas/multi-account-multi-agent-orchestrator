from concurrent.futures import ThreadPoolExecutor, as_completed

from models.schemas import Task, WorkerResult
from orchestrator.dependency_graph import TaskDependencyGraph
from account.account_manager import AccountManager


class Scheduler:
    """
    Coordinates Tasks, the Dependency Graph, and available Workers.

    Responsibilities:
    - Find tasks whose dependencies are satisfied
    - Assign tasks to available Workers
    - Execute independent tasks in parallel
    - Detect Worker failures
    - Retry failed tasks using another Worker
    - Allow the Master to request verification-based retries
    - Stop retrying after the configured limit
    - Collect Worker results

    The existing run() method is retained for backward
    compatibility with the current test suite.

    The Master can additionally use execute_ready_tasks()
    to introduce a proper Master-controlled verification gate.
    """

    def __init__(
        self,
        dependency_graph: TaskDependencyGraph,
        account_manager: AccountManager,
        max_retries: int = 1,
    ):
        self.dependency_graph = dependency_graph
        self.account_manager = account_manager
        self.max_retries = max_retries

        self.completed_tasks: set[str] = set()
        self.failed_tasks: set[str] = set()

        self.results: list[WorkerResult] = []

        self.retry_count: dict[str, int] = {}

    def run(self) -> list[WorkerResult]:
        """
        Execute all tasks while respecting dependencies.

        Independent tasks are executed in parallel.

        This is the original Scheduler execution path.

        It is intentionally retained so existing Scheduler
        behavior and tests remain stable.

        The newer Master-controlled execution path uses
        execute_ready_tasks().
        """

        while True:
            ready_tasks = self.dependency_graph.get_ready_tasks(
                self.completed_tasks
            )

            if not ready_tasks:
                break

            available_workers = (
                self.account_manager.get_available_workers()
            )

            if not available_workers:
                break

            tasks_to_run = ready_tasks[
                :len(available_workers)
            ]

            workers_to_use = available_workers[
                :len(tasks_to_run)
            ]

            with ThreadPoolExecutor(
                max_workers=len(workers_to_use)
            ) as executor:

                future_to_task = {}
                future_to_worker = {}

                for task, worker in zip(
                    tasks_to_run,
                    workers_to_use,
                ):
                    future = executor.submit(
                        self._execute_task,
                        task,
                        worker,
                    )

                    future_to_task[future] = task
                    future_to_worker[future] = worker

                for future in as_completed(
                    future_to_task
                ):
                    task = future_to_task[future]

                    worker = future_to_worker[
                        future
                    ]

                    try:
                        result = future.result()

                    except Exception as exc:
                        result = WorkerResult(
                            task_id=task.task_id,
                            worker_id=worker.worker_id,
                            status="failed",
                            files_changed=[],
                            notes=(
                                "Worker crashed "
                                "during execution."
                            ),
                            error=str(exc),
                        )

                    self._handle_result(
                        task=task,
                        result=result,
                        failed_worker_id=worker.worker_id,
                    )

        return self.results

    def execute_ready_tasks(
        self,
    ) -> list[tuple[Task, WorkerResult]]:
        """
        Execute the tasks that are currently ready.

        IMPORTANT:

        This method does NOT mark successful tasks as
        completed.

        That decision belongs to the Master after the
        Verification Gate approves the Worker result.

        This gives us the architecture:

            Ready Task
                ↓
            Scheduler
                ↓
            Worker
                ↓
          WorkerResult
                ↓
            Master
                ↓
        Verification Gate
                ↓
          PASS / FAIL
                ↓
        Master decides whether
        the task is completed

        Returns:
            List of (Task, WorkerResult) pairs.
        """

        ready_tasks = (
            self.dependency_graph.get_ready_tasks(
                self.completed_tasks
            )
        )

        if not ready_tasks:
            return []

        available_workers = (
            self.account_manager.get_available_workers()
        )

        if not available_workers:
            return []

        tasks_to_run = ready_tasks[
            :len(available_workers)
        ]

        workers_to_use = available_workers[
            :len(tasks_to_run)
        ]

        results = []

        with ThreadPoolExecutor(
            max_workers=len(workers_to_use)
        ) as executor:

            future_to_task = {}
            future_to_worker = {}

            for task, worker in zip(
                tasks_to_run,
                workers_to_use,
            ):
                future = executor.submit(
                    self._execute_task,
                    task,
                    worker,
                )

                future_to_task[future] = task
                future_to_worker[future] = worker

            for future in as_completed(
                future_to_task
            ):
                task = future_to_task[future]

                worker = future_to_worker[
                    future
                ]

                try:
                    result = future.result()

                except Exception as exc:
                    result = WorkerResult(
                        task_id=task.task_id,
                        worker_id=worker.worker_id,
                        status="failed",
                        files_changed=[],
                        notes=(
                            "Worker crashed "
                            "during execution."
                        ),
                        error=str(exc),
                    )

                results.append(
                    (task, result)
                )

        return results

    def _handle_result(
        self,
        task: Task,
        result: WorkerResult,
        failed_worker_id: str | None = None,
    ) -> None:
        """
        Handle a Worker result.

        Successful tasks are marked completed.

        Failed tasks are retried using another Worker.
        """

        if result.status == "completed":
            self.results.append(result)

            self.completed_tasks.add(
                task.task_id
            )

            self.dependency_graph.mark_completed(
                task.task_id
            )

            return

        retry_count = self.retry_count.get(
            task.task_id,
            0,
        )

        if retry_count < self.max_retries:
            self.retry_count[task.task_id] = (
                retry_count + 1
            )

            print(
                f"Retrying {task.task_id} "
                f"(attempt {retry_count + 1})"
            )

            retry_result = self._retry_task(
                task=task,
                excluded_worker_id=failed_worker_id,
            )

            if retry_result is not None:
                self._handle_result(
                    task=task,
                    result=retry_result,
                    failed_worker_id=failed_worker_id,
                )

                return

        print(
            f"Task {task.task_id} failed permanently."
        )

        self.failed_tasks.add(
            task.task_id
        )

        task.status = "failed"

        self.results.append(result)

    def _retry_task(
        self,
        task: Task,
        excluded_worker_id: str | None = None,
    ) -> WorkerResult | None:
        """
        Internal retry implementation.

        Searches for an available Worker other than
        the excluded Worker.
        """

        available_workers = [
            worker
            for worker in (
                self.account_manager
                .get_available_workers()
            )
            if worker.worker_id != excluded_worker_id
        ]

        if not available_workers:
            print(
                f"No alternative Worker available "
                f"for {task.task_id}."
            )

            return None

        worker = available_workers[0]

        return self._execute_task(
            task,
            worker,
        )

    def retry_task(
        self,
        task: Task,
        excluded_worker_id: str | None = None,
    ) -> WorkerResult | None:
        """
        Public retry interface used by the Master.

        The Master can call this method when the
        Verification Gate rejects a Worker result.

        The previously assigned Worker can be excluded
        so the task can be reassigned to another Worker.
        """

        return self._retry_task(
            task=task,
            excluded_worker_id=excluded_worker_id,
        )

    def mark_task_verified(
        self,
        task_id: str,
    ) -> None:
        """
        Mark a task as completed after the Master
        Verification Gate approves its result.

        This is the new verification-controlled
        completion boundary.

        The Scheduler does NOT call this automatically
        from execute_ready_tasks().
        """

        self.completed_tasks.add(
            task_id
        )

        self.dependency_graph.mark_completed(
            task_id
        )

    def mark_task_failed(
        self,
        task_id: str,
    ) -> None:
        """
        Mark a task as permanently failed.

        Failed tasks are not added to completed_tasks,
        therefore dependent tasks will not become ready.
        """

        self.failed_tasks.add(
            task_id
        )

        node_data = (
            self.dependency_graph.graph.nodes.get(
                task_id
            )
        )

        if node_data is not None:
            task = node_data["task"]
            task.status = "failed"

    def _execute_task(
        self,
        task: Task,
        worker,
    ) -> WorkerResult:
        """
        Execute one task using one Worker.

        The Worker is marked busy during execution
        and becomes available afterward.
        """

        self.account_manager.mark_busy(
            worker.worker_id
        )

        try:
            return worker.execute(task)

        finally:
            self.account_manager.mark_available(
                worker.worker_id
            )