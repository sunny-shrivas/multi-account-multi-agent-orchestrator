import networkx as nx

from models.schemas import Task


class TaskDependencyGraph:
    """
    Represents tasks and their dependencies as a directed graph.

    An edge A -> B means:
    Task B depends on Task A.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_task(self, task: Task) -> None:
        """
        Add a task and its dependencies to the graph.
        """

        self.graph.add_node(task.task_id, task=task)

        for dependency in task.dependencies:
            self.graph.add_edge(dependency, task.task_id)

    def add_tasks(self, tasks: list[Task]) -> None:
        """
        Add multiple tasks to the graph.
        """

        for task in tasks:
            self.add_task(task)

    def get_ready_tasks(self, completed_tasks: set[str]) -> list[Task]:
        """
        Return pending tasks whose dependencies have all been completed.
        """

        ready_tasks = []

        for task_id in self.graph.nodes:
            task = self.graph.nodes[task_id]["task"]

            # Skip tasks that are already completed.
            if task_id in completed_tasks:
                continue

            # Only pending tasks can become ready.
            if task.status != "pending":
                continue

            dependencies = task.dependencies

            # A task is ready only when every dependency is completed.
            if all(
                dependency in completed_tasks
                for dependency in dependencies
            ):
                ready_tasks.append(task)

        return ready_tasks

    def mark_completed(self, task_id: str) -> None:
        """
        Mark a task as completed in the graph.
        """

        if task_id in self.graph.nodes:
            task = self.graph.nodes[task_id]["task"]
            task.status = "completed"

    def validate(self) -> None:
        """
        Validate that the dependency graph does not contain cycles.
        """

        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError(
                "Task dependency graph contains a cycle."
            )