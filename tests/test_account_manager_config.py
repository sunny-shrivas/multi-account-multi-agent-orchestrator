from account.account_manager import AccountManager


def test_account_manager_loads_workers_from_config():
    """
    Verify that enabled Workers are created from
    configuration and disabled Workers are ignored.
    """

    account_manager = AccountManager()

    account_manager.load_from_config(
        "config/workers.test.yaml"
    )

    workers = (
        account_manager.get_available_workers()
    )

    assert len(workers) == 3

    worker_ids = {
        worker.worker_id
        for worker in workers
    }

    assert worker_ids == {
        "mock_001",
        "mock_002",
        "mock_003",
    }

    assert (
        account_manager.get_worker(
            "disabled_001"
        )
        is None
    )

    print("\nRegistered Workers:")

    for worker in workers:
        print(
            f"- {worker.worker_id}"
        )


if __name__ == "__main__":
    test_account_manager_loads_workers_from_config()

    print(
        "\nAccount Manager configuration test passed."
    )