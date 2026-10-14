import pytest

from orchestrator.plan_parser import PlanParser


def test_parse_numbered_project_plan():
    tasks = PlanParser.parse(
        """
        1. Design the API
        2. Implement authentication
        3. Write automated tests
        """
    )

    assert len(tasks) == 3
    assert tasks[0].task_id == "task_001"
    assert tasks[0].description == "Design the API"
    assert tasks[1].description == "Implement authentication"
    assert tasks[2].description == "Write automated tests"


def test_parse_explicit_dependencies_and_acceptance_criteria():
    tasks = PlanParser.parse(
        """
        1. Design the API
        2. Implement authentication
        """,
        dependencies={"task_002": ["task_001"]},
        acceptance_criteria={
            "task_001": ["Document endpoints"],
            "task_002": ["Validate credentials"],
        },
    )

    assert tasks[1].dependencies == ["task_001"]
    assert tasks[0].acceptance_criteria == ["Document endpoints"]
    assert tasks[1].acceptance_criteria == ["Validate credentials"]


def test_reject_empty_plan():
    with pytest.raises(ValueError, match="cannot be empty"):
        PlanParser.parse("  \n  ")


def test_reject_unknown_dependency():
    with pytest.raises(ValueError, match="unknown dependencies"):
        PlanParser.parse(
            "1. Build API",
            dependencies={"task_001": ["task_999"]},
        )


def test_reject_circular_dependencies():
    with pytest.raises(ValueError, match="cycle"):
        PlanParser.parse(
            """
            1. Build API
            2. Build UI
            """,
            dependencies={
                "task_001": ["task_002"],
                "task_002": ["task_001"],
            },
        )
