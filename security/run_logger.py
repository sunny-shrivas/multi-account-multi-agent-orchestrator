import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class RunLogger:
    """
    Records orchestration events in a JSON Lines file.

    Each line represents one event.

    The logger sanitizes sensitive fields before writing them
    to disk so credentials and other secrets are not persisted
    in the run log.
    """

    SENSITIVE_KEYWORDS = {
        "api_key",
        "apikey",
        "access_token",
        "auth_token",
        "authorization",
        "password",
        "passwd",
        "secret",
        "client_secret",
        "private_key",
        "credential",
        "credentials",
    }

    REDACTED_VALUE = "[REDACTED]"

    def __init__(
        self,
        log_path: str = "run.log",
    ):
        self.log_path = Path(log_path)

        parent_directory = self.log_path.parent

        parent_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def log_event(
        self,
        event: str,
        task_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Record one orchestration event.

        Sensitive fields inside details are recursively
        redacted before the event is persisted.
        """

        sanitized_details = self._sanitize(
            details or {}
        )

        event_record = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "event": event,
            "task_id": task_id,
            "worker_id": worker_id,
            "details": sanitized_details,
        }

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as log_file:
            log_file.write(
                json.dumps(
                    event_record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def read_events(
        self,
    ) -> list[dict[str, Any]]:
        """
        Read all recorded events.

        Returns an empty list when the log file does not
        contain any events yet.
        """

        if not self.log_path.exists():
            return []

        events = []

        with self.log_path.open(
            "r",
            encoding="utf-8",
        ) as log_file:
            for line in log_file:
                line = line.strip()

                if not line:
                    continue

                events.append(
                    json.loads(line)
                )

        return events

    def _sanitize(
        self,
        value: Any,
    ) -> Any:
        """
        Recursively sanitize dictionaries and lists.

        Any dictionary key containing a sensitive keyword
        is replaced with [REDACTED].
        """

        if isinstance(value, dict):
            sanitized = {}

            for key, item in value.items():
                key_string = str(key).lower()

                if self._is_sensitive_key(
                    key_string
                ):
                    sanitized[key] = (
                        self.REDACTED_VALUE
                    )
                else:
                    sanitized[key] = self._sanitize(
                        item
                    )

            return sanitized

        if isinstance(value, list):
            return [
                self._sanitize(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                self._sanitize(item)
                for item in value
            )

        return value

    def _is_sensitive_key(
        self,
        key: str,
    ) -> bool:
        """
        Determine whether a field name represents
        potentially sensitive information.
        """

        normalized_key = (
            key.lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        return any(
            keyword in normalized_key
            for keyword in self.SENSITIVE_KEYWORDS
        )