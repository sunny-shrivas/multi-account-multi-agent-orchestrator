from pathlib import Path

import yaml


def test_worker_configuration():
    """
    Verify that the Worker configuration can be loaded
    from YAML.
    """

    config_path = Path(
        "config/workers.example.yaml"
    )

    assert config_path.exists()

    with open(
        config_path,
        "r",
        encoding="utf-8",
    ) as file:
        config = yaml.safe_load(file)

    assert "workers" in config

    workers = config["workers"]

    assert len(workers) == 4

    worker_ids = [
        worker["worker_id"]
        for worker in workers
    ]

    assert "openai_001" in worker_ids
    assert "claude_001" in worker_ids
    assert "mock_001" in worker_ids
    assert "mock_002" in worker_ids

    print("\nConfigured Workers:")

    for worker in workers:
        print(
            f"- {worker['worker_id']} | "
            f"{worker['provider']} | "
            f"{worker['worker_type']} | "
            f"enabled={worker['enabled']}"
        )


if __name__ == "__main__":
    test_worker_configuration()

    print(
        "\nWorker configuration test passed."
    )