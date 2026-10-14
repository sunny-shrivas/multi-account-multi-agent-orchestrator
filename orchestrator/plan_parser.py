import re
from collections.abc import Sequence

from models.schemas import Task


class PlanParser:
    """
    Deterministically convert a written project plan into Tasks.

    Supported input:
    - Numbered steps, such as "1. Design the API"
    - Bulleted steps, such as "- Implement authentication"
    - One task per non-empty line

    This parser does not use an LLM. Dependencies and acceptance
    criteria can be supplied explicitly for more precise plans.
    """

    _STEP_PREFIX = re.compile(
        r"^\s*(?:(?:[-*•])\s+|(?:\d+[.)])\s+|(?:step\s+\d+[:.)]?\s+))",
        re.IGNORECASE,
    )

    @classmethod
    def parse(
        cls,
        project_plan: str,
        *,
        acceptance_criteria: dict[str, list[str]] | None = None,
        dependencies: dict[str, list[str]] | None = None,
    ) -> list[Task]:
        """
        Convert plan lines into Task objects.

        Args:
            project_plan: Numbered, bulleted, or line-separated steps.
            acceptance_criteria: Optional criteria keyed by generated
                task ID, e.g. {"task_001": ["Tests pass"]}.
            dependencies: Optional dependencies keyed by generated
                task ID, e.g. {"task_002": ["task_001"]}.

        Returns:
            A validated list of Task objects.

        Raises:
            ValueError: If the plan is empty, has duplicate task IDs,
                or references unknown dependencies.
        """
        if not isinstance(project_plan, str) or not project_plan.strip():
            raise ValueError("Project plan cannot be empty.")

        lines = [
            line.strip()
            for line in project_plan.splitlines()
            if line.strip()
        ]

        descriptions: list[str] = []

        for line in lines:
            description = cls._STEP_PREFIX.sub("", line).strip()

            if description:
                descriptions.append(description)

        if not descriptions:
            raise ValueError(
                "Project plan must contain at least one task."
            )

        criteria_by_id = acceptance_criteria or {}
        dependencies_by_id = dependencies or {}

        task_ids = {
            f"task_{index:03d}"
            for index in range(1, len(descriptions) + 1)
        }

        for task_id, task_dependencies in dependencies_by_id.items():
            if task_id not in task_ids:
                raise ValueError(
                    f"Dependencies supplied for unknown task: {task_id}"
                )

            unknown = set(task_dependencies) - task_ids
            if unknown:
                raise ValueError(
                    f"Task {task_id} references unknown dependencies: "
                    f"{', '.join(sorted(unknown))}"
                )

        for task_id in criteria_by_id:
            if task_id not in task_ids:
                raise ValueError(
                    f"Acceptance criteria supplied for unknown task: "
                    f"{task_id}"
                )

        tasks = []

        for index, description in enumerate(descriptions, start=1):
            task_id = f"task_{index:03d}"

            tasks.append(
                Task(
                    task_id=task_id,
                    description=description,
                    dependencies=dependencies_by_id.get(task_id, []),
                    acceptance_criteria=criteria_by_id.get(task_id, []),
                )
            )

        cls._validate_dependency_cycles(tasks)

        return tasks

    @staticmethod
    def _validate_dependency_cycles(tasks: Sequence[Task]) -> None:
        """Reject circular task dependencies."""
        dependencies = {
            task.task_id: task.dependencies
            for task in tasks
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise ValueError(
                    "Task dependencies contain a cycle."
                )

            if task_id in visited:
                return

            visiting.add(task_id)

            for dependency in dependencies[task_id]:
                visit(dependency)

            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in dependencies:
            visit(task_id)
