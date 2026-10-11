from pydantic import BaseModel, Field
from typing import List, Optional


class Task(BaseModel):
    """
    Represents one unit of work in the project plan.
    """

    task_id: str

    description: str

    dependencies: List[str] = Field(
        default_factory=list
    )

    acceptance_criteria: List[str] = Field(
        default_factory=list
    )

    status: str = "pending"

    assigned_worker: Optional[str] = None


class WorkerResult(BaseModel):
    """
    Standardized result returned by every Worker.

    worker_id identifies which Worker produced the result.
    This allows the Master to exclude a failed or rejected
    Worker during reassignment.
    """

    task_id: str

    worker_id: str

    status: str

    files_changed: List[str] = Field(
        default_factory=list
    )

    notes: str = ""

    error: Optional[str] = None