from abc import ABC, abstractmethod
from pathlib import Path

from models.schemas import Task, WorkerResult
from security.workspace_files import WorkspaceFileManager
from security.workspace_guard import WorkspaceGuard


class BaseWorker(ABC):
    """
    Common interface for every Worker in the system.

    Every Worker receives:

    - An isolated workspace
    - A WorkspaceGuard for path validation
    - A WorkspaceFileManager for safe file operations

    Concrete Workers such as OpenAIWorker, ClaudeWorker,
    and MockWorker inherit from this class.
    """

    def __init__(
        self,
        worker_id: str,
        workspace_guard: WorkspaceGuard | None = None,
    ):
        self.worker_id = worker_id

        self.workspace_guard = (
            workspace_guard
            or WorkspaceGuard()
        )

        self.workspace: Path = (
            self.workspace_guard.create_workspace(
                worker_id
            )
        )

        self.file_manager = (
            WorkspaceFileManager(
                worker_id=worker_id,
                workspace_guard=self.workspace_guard,
            )
        )

    def validate_workspace_path(
        self,
        path: str,
    ) -> Path:
        """
        Validate that a Worker path remains inside
        the Worker's isolated workspace.
        """

        return self.workspace_guard.validate_path(
            worker_id=self.worker_id,
            path=path,
        )

    def write_file(
        self,
        relative_path: str,
        content: str,
    ) -> Path:
        """
        Safely write a file inside the Worker's
        workspace.

        This is a convenience method that delegates
        to WorkspaceFileManager.
        """

        return self.file_manager.write_file(
            relative_path=relative_path,
            content=content,
        )

    def read_file(
        self,
        relative_path: str,
    ) -> str:
        """
        Safely read a file from the Worker's
        workspace.
        """

        return self.file_manager.read_file(
            relative_path=relative_path
        )

    def list_files(self) -> list[str]:
        """
        List all files inside the Worker's workspace.
        """

        return self.file_manager.list_files()

    def get_changed_files(self) -> list[str]:
        """
        Return files written during the Worker's
        execution lifecycle.
        """

        return self.file_manager.get_changed_files()

    @abstractmethod
    def execute(
        self,
        task: Task,
    ) -> WorkerResult:
        """
        Execute a task and return a standardized
        WorkerResult.

        Every concrete Worker must implement this method.
        """
        pass