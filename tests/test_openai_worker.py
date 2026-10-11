from types import SimpleNamespace
from unittest.mock import patch

from models.schemas import Task
from workers.openai_worker import OpenAIWorker


class FakeResponses:
    """Simulates the OpenAI Responses API."""

    def __init__(
        self,
        output_text="A sample task deliverable.",
        error=None,
    ):
        self.output_text = output_text
        self.error = error
        self.last_model = None
        self.last_input = None

    def create(self, model, input):
        self.last_model = model
        self.last_input = input

        if self.error:
            raise self.error

        return SimpleNamespace(
            output_text=self.output_text
        )


class FakeOpenAIClient:
    """Fake client that does not make network requests."""

    def __init__(self, responses):
        self.responses = responses


def make_task():
    return Task(
        task_id="task_001",
        description="Design a REST API",
        acceptance_criteria=[
            "Define API endpoints",
            "Describe error handling",
        ],
    )


def test_openai_worker_success():
    fake_responses = FakeResponses(
        output_text=(
            "Define API endpoints: "
            "GET /items and POST /items. "
            "Describe error handling: "
            "return appropriate HTTP status codes."
        )
    )

    worker = OpenAIWorker(
        worker_id="openai_001",
        model="gpt-4.1-mini",
        client=FakeOpenAIClient(fake_responses),
    )

    result = worker.execute(make_task())

    assert result.task_id == "task_001"
    assert result.status == "completed"

    assert result.files_changed == [
        "output/result.md"
    ]

    artifact_path = (
        worker.workspace
        / "output"
        / "result.md"
    )

    assert artifact_path.exists()
    assert artifact_path.is_file()

    assert artifact_path.read_text(
        encoding="utf-8"
    ) == result.notes

    assert "GET /items" in result.notes

    assert (
        fake_responses.last_model
        == "gpt-4.1-mini"
    )


def test_openai_worker_empty_response():
    worker = OpenAIWorker(
        worker_id="openai_001",
        client=FakeOpenAIClient(
            FakeResponses(
                output_text=""
            )
        ),
    )

    result = worker.execute(make_task())

    assert result.status == "failed"

    assert result.error == (
        "Empty model response."
    )

    assert result.files_changed == []


def test_openai_worker_api_error():
    worker = OpenAIWorker(
        worker_id="openai_001",
        client=FakeOpenAIClient(
            FakeResponses(
                error=RuntimeError(
                    "Simulated API failure"
                )
            )
        ),
    )

    result = worker.execute(make_task())

    assert result.status == "failed"

    assert result.error == (
        "OpenAI request failed: RuntimeError"
    )

    assert result.files_changed == []


def test_openai_worker_requires_api_key_without_client(
    monkeypatch,
):
    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    with patch(
        "workers.openai_worker.load_dotenv"
    ):
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            try:
                OpenAIWorker(
                    worker_id="openai_001",
                    api_key="",
                )

                assert False, (
                    "Expected missing-key error."
                )

            except ValueError as exc:
                assert (
                    "OPENAI_API_KEY is missing"
                    in str(exc)
                )


if __name__ == "__main__":
    test_openai_worker_success()
    test_openai_worker_empty_response()
    test_openai_worker_api_error()

    print(
        "\nOpenAI Worker tests completed."
    )