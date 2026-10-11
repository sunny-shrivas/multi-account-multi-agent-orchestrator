from pathlib import Path

from security.run_logger import RunLogger


def test_run_logger_redacts_sensitive_fields(
    tmp_path: Path,
):
    log_path = tmp_path / "secure_run.log"

    logger = RunLogger(
        log_path=str(log_path)
    )

    logger.log_event(
        event="TEST_SECRET",
        task_id="task_001",
        worker_id="worker_001",
        details={
            "api_key": "sk-secret-value",
            "access_token": "secret-token",
            "password": "super-secret-password",
            "normal_field": "safe-value",
        },
    )

    log_contents = log_path.read_text(
        encoding="utf-8"
    )

    assert "sk-secret-value" not in log_contents
    assert "secret-token" not in log_contents
    assert "super-secret-password" not in log_contents

    assert "safe-value" in log_contents