import json

from security.run_logger import RunLogger


def test_run_logger_records_event(tmp_path):
    """
    Verify that an orchestration event is written
    to the log.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="TASK_ASSIGNED",
        task_id="task_001",
        worker_id="worker_001",
        details={
            "attempt": 1,
        },
    )

    events = logger.read_events()

    assert len(events) == 1

    event = events[0]

    assert event["event"] == "TASK_ASSIGNED"

    assert event["task_id"] == "task_001"

    assert event["worker_id"] == "worker_001"

    assert event["details"]["attempt"] == 1

    assert "timestamp" in event


def test_run_logger_records_multiple_events(tmp_path):
    """
    Verify that multiple events are preserved in order.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="TASK_ASSIGNED",
        task_id="task_001",
        worker_id="worker_001",
    )

    logger.log_event(
        event="WORKER_STARTED",
        task_id="task_001",
        worker_id="worker_001",
    )

    logger.log_event(
        event="WORKER_COMPLETED",
        task_id="task_001",
        worker_id="worker_001",
    )

    events = logger.read_events()

    assert len(events) == 3

    assert events[0]["event"] == "TASK_ASSIGNED"

    assert events[1]["event"] == "WORKER_STARTED"

    assert (
        events[2]["event"]
        == "WORKER_COMPLETED"
    )


def test_run_logger_creates_log_directory(tmp_path):
    """
    Verify that the logger creates missing parent
    directories automatically.
    """

    log_path = (
        tmp_path
        / "logs"
        / "orchestrator"
        / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="TASK_STARTED",
        task_id="task_001",
    )

    assert log_path.exists()


def test_run_logger_writes_valid_json_lines(tmp_path):
    """
    Verify that every physical log line is valid JSON.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="VERIFICATION_PASSED",
        task_id="task_001",
    )

    with log_path.open(
        "r",
        encoding="utf-8",
    ) as log_file:

        lines = log_file.readlines()

    assert len(lines) == 1

    parsed_event = json.loads(
        lines[0]
    )

    assert (
        parsed_event["event"]
        == "VERIFICATION_PASSED"
    )


def test_run_logger_empty_log(tmp_path):
    """
    Verify that a new logger returns no events
    before anything is recorded.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    assert logger.read_events() == []


def test_run_logger_optional_fields_are_none(tmp_path):
    """
    Verify that task_id and worker_id are optional
    and are stored as null when omitted.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="EXECUTION_STARTED"
    )

    events = logger.read_events()

    assert len(events) == 1

    event = events[0]

    assert event["event"] == "EXECUTION_STARTED"

    assert event["task_id"] is None

    assert event["worker_id"] is None

    assert event["details"] == {}


def test_run_logger_preserves_nested_details(tmp_path):
    """
    Verify that structured event details are preserved
    correctly in JSON.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="TASK_REASSIGNED",
        task_id="task_002",
        worker_id="worker_002",
        details={
            "attempt": 2,
            "excluded_worker": "worker_001",
            "reason": "verification_failed",
        },
    )

    events = logger.read_events()

    assert len(events) == 1

    details = events[0]["details"]

    assert details["attempt"] == 2

    assert (
        details["excluded_worker"]
        == "worker_001"
    )

    assert (
        details["reason"]
        == "verification_failed"
    )


def test_run_logger_preserves_special_characters(tmp_path):
    """
    Verify that JSON encoding safely preserves special
    characters inside log details.
    """

    log_path = (
        tmp_path / "run.log"
    )

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="WORKER_COMPLETED",
        task_id="task_003",
        details={
            "message": (
                'Worker completed "successfully" '
                "with\nmultiple lines."
            )
        },
    )

    events = logger.read_events()

    assert len(events) == 1

    message = (
        events[0]["details"]["message"]
    )

    assert (
        message
        == 'Worker completed "successfully" '
        "with\nmultiple lines."
    )


if __name__ == "__main__":
    test_run_logger_records_event(
        __import__("pathlib").Path(".")
    )