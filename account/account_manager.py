import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv

from workers.base_worker import BaseWorker
from workers.mock_worker import MockWorker
from workers.success_mock_worker import SuccessMockWorker
from workers.openai_worker import OpenAIWorker
from workers.claude_worker import ClaudeWorker


class AccountManager:
    """
    Manages the Workers/accounts available to the
    Master Orchestrator.

    Workers are registered from configuration rather than
    being hard-coded inside the Master.

    The AccountManager is responsible for:

    - Reading Worker configuration
    - Creating the correct Worker implementation
    - Resolving API keys from environment variables
    - Registering Workers
    - Tracking Worker availability
    - Keeping provider/account details away from the Master
    """

    def __init__(self):
        load_dotenv()

        self.workers: Dict[str, BaseWorker] = {}
        self.busy_workers: set[str] = set()

    def register_worker(self, worker: BaseWorker) -> None:
        """
        Register a Worker in the Worker pool.
        """

        if worker.worker_id in self.workers:
            raise ValueError(
                f"Worker already registered: {worker.worker_id}"
            )

        self.workers[worker.worker_id] = worker

    def get_worker(
        self,
        worker_id: str,
    ) -> Optional[BaseWorker]:
        """
        Retrieve a Worker by ID.
        """

        return self.workers.get(worker_id)

    def get_available_workers(
        self,
    ) -> List[BaseWorker]:
        """
        Return all Workers that are currently available.
        """

        return [
            worker
            for worker_id, worker in self.workers.items()
            if worker_id not in self.busy_workers
        ]

    def mark_busy(
        self,
        worker_id: str,
    ) -> None:
        """
        Mark a Worker as busy.
        """

        if worker_id in self.workers:
            self.busy_workers.add(worker_id)

    def mark_available(
        self,
        worker_id: str,
    ) -> None:
        """
        Mark a Worker as available again.
        """

        self.busy_workers.discard(worker_id)

    def load_from_config(
        self,
        config_path: str,
    ) -> None:
        """
        Load Worker definitions from a YAML configuration file.
        """

        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Worker configuration not found: {config_path}"
            )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            config = yaml.safe_load(file)

        if not config or "workers" not in config:
            raise ValueError(
                "Configuration must contain a 'workers' section."
            )

        for worker_config in config["workers"]:
            if not worker_config.get(
                "enabled",
                True,
            ):
                continue

            worker_id = worker_config.get(
                "worker_id"
            )

            provider = worker_config.get(
                "provider"
            )

            worker_type = worker_config.get(
                "worker_type"
            )

            if not worker_id:
                raise ValueError(
                    "Worker configuration is missing "
                    "'worker_id'."
                )

            if not provider:
                raise ValueError(
                    f"Worker '{worker_id}' is missing "
                    "'provider'."
                )

            if not worker_type:
                raise ValueError(
                    f"Worker '{worker_id}' is missing "
                    "'worker_type'."
                )

            worker = self._create_worker(
                worker_id=worker_id,
                provider=provider,
                worker_type=worker_type,
                worker_config=worker_config,
            )

            self.register_worker(worker)

    def _create_worker(
        self,
        worker_id: str,
        provider: str,
        worker_type: str,
        worker_config: dict,
    ) -> BaseWorker:
        """
        Create a Worker implementation based on configuration.
        """

        normalized_provider = (
            provider.lower().strip()
        )

        normalized_worker_type = (
            worker_type.lower().strip()
        )

        # --------------------------------------------------
        # Generic Mock Worker
        # --------------------------------------------------

        if normalized_worker_type == "mock":
            return MockWorker(
                worker_id=worker_id
            )

        # --------------------------------------------------
        # Successful Mock Worker
        # --------------------------------------------------

        if normalized_worker_type == "success_mock":
            return SuccessMockWorker(
                worker_id=worker_id
            )

        # --------------------------------------------------
        # Live Workers
        # --------------------------------------------------

        if normalized_worker_type != "live":
            raise ValueError(
                f"Unsupported worker_type "
                f"'{worker_type}' for Worker "
                f"'{worker_id}'."
            )

        # --------------------------------------------------
        # OpenAI Worker
        # --------------------------------------------------

        if normalized_provider == "openai":
            api_key = self._resolve_api_key(
                worker_config=worker_config,
                provider="OpenAI",
            )

            model = worker_config.get(
                "model"
            )

            return OpenAIWorker(
                worker_id=worker_id,
                model=model,
                api_key=api_key,
            )

        # --------------------------------------------------
        # Anthropic / Claude Worker
        # --------------------------------------------------

        if normalized_provider in {
            "anthropic",
            "claude",
        }:
            api_key = self._resolve_api_key(
                worker_config=worker_config,
                provider="Anthropic",
            )

            model = worker_config.get(
                "model"
            )

            return ClaudeWorker(
                worker_id=worker_id,
                model=model,
                api_key=api_key,
            )

        raise ValueError(
            f"Unsupported provider "
            f"'{provider}' for Worker "
            f"'{worker_id}'."
        )

    def _resolve_api_key(
        self,
        worker_config: dict,
        provider: str,
    ) -> str:
        """
        Resolve an API key from an environment variable.

        The actual secret is never stored in the YAML file.
        Only the environment variable name is configured.
        """

        api_key_env = worker_config.get(
            "api_key_env"
        )

        if not api_key_env:
            raise ValueError(
                f"{provider} Worker is missing "
                "'api_key_env' in configuration."
            )

        api_key = os.getenv(
            api_key_env
        )

        if not api_key:
            raise ValueError(
                f"Environment variable "
                f"'{api_key_env}' is not configured "
                f"for the {provider} Worker."
            )

        return api_key