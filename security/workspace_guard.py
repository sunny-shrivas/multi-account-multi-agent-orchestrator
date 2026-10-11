from pathlib import Path


class WorkspaceGuard:
    """
    Creates and validates isolated workspaces for Workers.

    Each Worker receives its own directory under the
    project's workspaces/ directory.
    """

    def __init__(self, base_directory: str = "workspaces"):
        self.base_directory = Path(base_directory).resolve()

        # Make sure the base workspace directory exists.
        self.base_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def create_workspace(self, worker_id: str) -> Path:
        """
        Create and return an isolated workspace for a Worker.
        """

        worker_workspace = (
            self.base_directory / worker_id
        ).resolve()

        self._validate_path(worker_workspace)

        worker_workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        return worker_workspace

    def validate_path(
        self,
        worker_id: str,
        path: str,
    ) -> Path:
        """
        Validate that a requested path belongs to the
        specified Worker's workspace.

        Raises ValueError if the path attempts to escape
        the Worker workspace.
        """

        worker_workspace = (
            self.base_directory / worker_id
        ).resolve()

        requested_path = (
            worker_workspace / path
        ).resolve()

        self._validate_path(
            requested_path,
            worker_workspace,
        )

        return requested_path

    def _validate_path(
        self,
        path: Path,
        allowed_directory: Path | None = None,
    ) -> None:
        """
        Ensure a path remains inside the allowed directory.
        """

        if allowed_directory is None:
            allowed_directory = self.base_directory

        try:
            path.relative_to(allowed_directory)

        except ValueError:
            raise ValueError(
                "Workspace security violation: "
                "path escapes the allowed workspace."
            )