from pathlib import Path

from security.workspace_guard import WorkspaceGuard


class WorkspaceFileManager:
    """
    Provides safe file operations for a Worker.

    All file operations are restricted to the Worker's
    isolated workspace.

    The File Manager is intentionally small for the POC.
    It provides:

    - write_file()
    - read_file()
    - list_files()
    - reset_changed_files()
    - get_changed_files()

    Every path is validated through WorkspaceGuard before
    any filesystem operation occurs.
    """

    def __init__(
        self,
        worker_id: str,
        workspace_guard: WorkspaceGuard,
    ):
        self.worker_id = worker_id
        self.workspace_guard = workspace_guard

        self.workspace = (
            self.workspace_guard.create_workspace(
                worker_id
            )
        )

        self._changed_files: list[str] = []

    def reset_changed_files(self) -> None:
        """
        Reset the changed-file tracking for a new
        Worker execution.

        This prevents files reported from a previous task
        from appearing in the result of the next task.
        """

        self._changed_files.clear()

    def write_file(
        self,
        relative_path: str,
        content: str,
    ) -> Path:
        """
        Safely create or overwrite a file inside the
        Worker's workspace.

        Returns the absolute file path.

        Raises ValueError if the path attempts to escape
        the Worker workspace.
        """

        file_path = (
            self.workspace_guard.validate_path(
                worker_id=self.worker_id,
                path=relative_path,
            )
        )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path.write_text(
            content,
            encoding="utf-8",
        )

        relative_file = file_path.relative_to(
            self.workspace
        )

        relative_file_string = str(
            relative_file
        )

        if relative_file_string not in self._changed_files:
            self._changed_files.append(
                relative_file_string
            )

        return file_path

    def read_file(
        self,
        relative_path: str,
    ) -> str:
        """
        Safely read a file from the Worker's workspace.

        Raises ValueError if the path attempts to escape
        the Worker workspace.
        """

        file_path = (
            self.workspace_guard.validate_path(
                worker_id=self.worker_id,
                path=relative_path,
            )
        )

        if not file_path.is_file():
            raise FileNotFoundError(
                f"File does not exist: "
                f"{relative_path}"
            )

        return file_path.read_text(
            encoding="utf-8"
        )

    def list_files(self) -> list[str]:
        """
        Return all files currently present inside the
        Worker's workspace.

        Returned paths are relative to the Worker
        workspace.
        """

        files = []

        for path in self.workspace.rglob("*"):

            if not path.is_file():
                continue

            relative_path = path.relative_to(
                self.workspace
            )

            files.append(
                str(relative_path)
            )

        return sorted(files)

    def get_changed_files(self) -> list[str]:
        """
        Return files written through this File Manager
        during the current Worker execution lifecycle.
        """

        return list(self._changed_files)