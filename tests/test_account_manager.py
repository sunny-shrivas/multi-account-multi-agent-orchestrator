import os

import pytest

from account.account_manager import AccountManager
from workers.claude_worker import ClaudeWorker
from workers.mock_worker import MockWorker
from workers.openai_worker import OpenAIWorker


def test_load_mock_workers_from_config():
    """
    Verify that mock Workers are correctly loaded
    from the test configuration.
    """

    manager = AccountManager()

    manager.load_from_config(
        "config/workers.test.yaml"
    )

    assert set(manager.workers.keys()) == {
        "mock_001",
        "mock_002",
        "mock_003",
    }

    assert isinstance(
        manager.get_worker("mock_001"),
        MockWorker,
    )

    assert isinstance(
        manager.get_worker("mock_002"),
        MockWorker,
    )

    assert isinstance(
        manager.get_worker("mock_003"),
        MockWorker,
    )


def test_load_live_workers_from_config(monkeypatch):
    """
    Verify that OpenAI and Claude Workers are created
    from configuration.

    Fake API keys are used so no real API call occurs.
    """

    monkeypatch.setenv(
        "TEST_OPENAI_KEY",
        "fake-openai-key",
    )

    monkeypatch.setenv(
        "TEST_ANTHROPIC_KEY",
        "fake-anthropic-key",
    )

    manager = AccountManager()

    config_path = (
        "config/workers.test_live.yaml"
    )

    manager.load_from_config(
        config_path
    )

    assert isinstance(
        manager.get_worker("openai_test"),
        OpenAIWorker,
    )

    assert isinstance(
        manager.get_worker("claude_test"),
        ClaudeWorker,
    )

    assert isinstance(
        manager.get_worker("mock_test"),
        MockWorker,
    )


def test_disabled_worker_is_skipped(tmp_path):
    """
    Verify that disabled Workers are not registered.
    """

    config_file = tmp_path / "workers.yaml"

    config_file.write_text(
        """
workers:
  - worker_id: enabled_worker
    provider: mock
    worker_type: mock
    enabled: true

  - worker_id: disabled_worker
    provider: mock
    worker_type: mock
    enabled: false
""",
        encoding="utf-8",
    )

    manager = AccountManager()

    manager.load_from_config(
        str(config_file)
    )

    assert (
        "enabled_worker"
        in manager.workers
    )

    assert (
        "disabled_worker"
        not in manager.workers
    )


def test_missing_api_key_env_is_rejected(
    tmp_path,
):
    """
    Verify that a live Worker configuration without
    api_key_env is rejected.
    """

    config_file = tmp_path / "workers.yaml"

    config_file.write_text(
        """
workers:
  - worker_id: openai_test
    provider: openai
    worker_type: live
    enabled: true
""",
        encoding="utf-8",
    )

    manager = AccountManager()

    with pytest.raises(
        ValueError,
        match="api_key_env",
    ):
        manager.load_from_config(
            str(config_file)
        )


def test_missing_environment_variable_is_rejected(
    tmp_path,
    monkeypatch,
):
    """
    Verify that a configured API key environment
    variable must actually exist.
    """

    monkeypatch.delenv(
        "MISSING_TEST_API_KEY",
        raising=False,
    )

    config_file = tmp_path / "workers.yaml"

    config_file.write_text(
        """
workers:
  - worker_id: openai_test
    provider: openai
    worker_type: live
    api_key_env: MISSING_TEST_API_KEY
    enabled: true
""",
        encoding="utf-8",
    )

    manager = AccountManager()

    with pytest.raises(
        ValueError,
        match="MISSING_TEST_API_KEY",
    ):
        manager.load_from_config(
            str(config_file)
        )


def test_duplicate_worker_id_is_rejected(
    tmp_path,
):
    """
    Verify that two Workers cannot use the same
    Worker ID.
    """

    config_file = tmp_path / "workers.yaml"

    config_file.write_text(
        """
workers:
  - worker_id: duplicate_worker
    provider: mock
    worker_type: mock
    enabled: true

  - worker_id: duplicate_worker
    provider: mock
    worker_type: mock
    enabled: true
""",
        encoding="utf-8",
    )

    manager = AccountManager()

    with pytest.raises(
        ValueError,
        match="Worker already registered",
    ):
        manager.load_from_config(
            str(config_file)
        )