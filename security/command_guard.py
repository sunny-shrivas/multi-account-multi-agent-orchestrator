import shlex


class CommandGuard:
    """
    Validates shell commands before a Worker is allowed
    to execute them.

    The goal is to block high-risk operations while
    allowing normal development commands.
    """

    BLOCKED_PATTERNS = [
        "rm -rf",
        "git push --force",
        "git push -f",
        "git reset --hard",
        "git clean -fd",
        "docker system prune",
        "kubectl delete",
        "terraform destroy",
    ]

    def is_allowed(self, command: str) -> bool:
        """
        Return True when the command is considered safe.

        Return False when the command matches a blocked
        high-risk operation.
        """

        normalized_command = " ".join(
            shlex.split(command)
        ).lower()

        for pattern in self.BLOCKED_PATTERNS:
            if pattern.lower() in normalized_command:
                return False

        return True

    def validate(self, command: str) -> None:
        """
        Validate a command.

        Raises ValueError when the command is blocked.
        """

        if not self.is_allowed(command):
            raise ValueError(
                f"Blocked potentially dangerous command: "
                f"{command}"
            )