from types import SimpleNamespace

from models.schemas import Task
from workers.claude_worker import ClaudeWorker


class FakeClaudeClient:
    """
    Fake Anthropic client used for deterministic testing.

    No real Claude API request is made.
    """

    def __init__(self, response):
        self.messages = FakeMessages(response)


class FakeMessages:
    """
    Simulates the Anthropic messages API.
    """

    def __init__(self, response):
        self.response = response

    def create(
        self,
        model,
        max_tokens,
        messages,
    ):
        return self.response


def test_claude_worker_success():
    """
    Verify that ClaudeWorker converts a successful
    Claude response into a standardized WorkerResult.
    """

    fake_response = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="text",
                text=(
                    "API endpoints are defined. "
                    "Error handling is documented."
                ),
            )
        ]
    )

    worker = ClaudeWorker(
        worker_id="claude_test",
        model="test-model",
        client=FakeClaudeClient(
            fake_response
        ),
    )

    task = Task(
        task_id="task_001",
        description="Design a REST API",
        acceptance_criteria=[
            "API endpoints are defined",
            "Error handling is documented",
        ],
    )

    result = worker.execute(task)

    assert result.task_id == "task_001"
    assert result.worker_id == "claude_test"
    assert result.status == "completed"
    assert result.error is None

    assert (
        "API endpoints are defined"
        in result.notes
    )

    assert (
        "Error handling is documented"
        in result.notes
    )


def test_claude_worker_empty_response():
    """
    Verify that ClaudeWorker handles an empty Claude
    response as a failed WorkerResult.
    """

    fake_response = SimpleNamespace(
        content=[]
    )

    worker = ClaudeWorker(
        worker_id="claude_test",
        model="test-model",
        client=FakeClaudeClient(
            fake_response
        ),
    )

    task = Task(
        task_id="task_002",
        description="Generate documentation",
    )

    result = worker.execute(task)

    assert result.task_id == "task_002"
    assert result.worker_id == "claude_test"
    assert result.status == "failed"
    assert result.error == "Empty model response."


def test_claude_worker_api_error():
    """
    Verify that ClaudeWorker converts an API exception
    into a standardized failed WorkerResult.
    """

    class ErrorMessages:
        def create(
            self,
            model,
            max_tokens,
            messages,
        ):
            raise RuntimeError(
                "Simulated Claude API failure"
            )

    class ErrorClient:
        def __init__(self):
            self.messages = ErrorMessages()

    worker = ClaudeWorker(
        worker_id="claude_test",
        model="test-model",
        client=ErrorClient(),
    )

    task = Task(
        task_id="task_003",
        description="Generate documentation",
    )

    result = worker.execute(task)

    assert result.task_id == "task_003"
    assert result.worker_id == "claude_test"
    assert result.status == "failed"

    assert (
        result.error
        == "Claude request failed: RuntimeError"
    )


def test_claude_worker_requires_api_key_without_client(
):
    """
    Verify that ClaudeWorker requires an API key when
    no client is injected.
    """

    try:
        ClaudeWorker(
            worker_id="claude_test",
            api_key=None,
        )

    except ValueError as exc:

        assert (
            "ANTHROPIC_API_KEY is missing"
            in str(exc)
        )

    else:
        raise AssertionError(
            "ClaudeWorker should require "
            "ANTHROPIC_API_KEY when no client "
            "is provided."
        )