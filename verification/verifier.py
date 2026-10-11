from pathlib import Path

from models.schemas import Task, WorkerResult


class VerificationGate:
    """
    Verifies Worker output against the acceptance criteria
    defined in the Task.

    Verification is performed against the actual artifact
    produced by the Worker rather than relying only on the
    WorkerResult notes.

    Verification checks:

    1. Worker status must be "completed".
    2. Worker must report at least one changed file.
    3. Every reported file must actually exist.
    4. Every reported file must remain inside the Worker's
       isolated workspace.
    5. The artifact content must satisfy every acceptance
       criterion.

    The VerificationGate is deliberately deterministic for
    the first version of the POC.
    """

    def verify(
        self,
        task: Task,
        result: WorkerResult,
    ) -> bool:
        """
        Verify a WorkerResult against the actual Worker
        artifacts.

        Returns True only when all verification checks pass.
        """

        # --------------------------------------------------
        # Check 1: Worker must report successful completion.
        # --------------------------------------------------

        if result.status != "completed":
            return False

        # --------------------------------------------------
        # Check 2: A successful Worker must report at least
        # one delivered artifact.
        # --------------------------------------------------

        if not result.files_changed:
            return False

        # --------------------------------------------------
        # Determine the Worker's isolated workspace.
        #
        # Worker workspaces are stored under:
        #
        #     workspaces/<worker_id>/
        #
        # The worker_id comes from the standardized
        # WorkerResult contract.
        # --------------------------------------------------

        workspace = (
            Path("workspaces")
            / result.worker_id
        ).resolve()

        if not workspace.exists():
            return False

        if not workspace.is_dir():
            return False

        # --------------------------------------------------
        # Check every artifact reported by the Worker.
        # --------------------------------------------------

        artifact_contents = []

        for relative_file in result.files_changed:

            try:
                artifact_path = (
                    workspace
                    / relative_file
                ).resolve()

                # ------------------------------------------
                # Check 4: Artifact must remain inside the
                # Worker's isolated workspace.
                # ------------------------------------------

                artifact_path.relative_to(
                    workspace
                )

            except ValueError:
                return False

            # ----------------------------------------------
            # Check 3: Artifact must actually exist and be
            # a regular file.
            # ----------------------------------------------

            if not artifact_path.exists():
                return False

            if not artifact_path.is_file():
                return False

            # ----------------------------------------------
            # Read the actual artifact content.
            # ----------------------------------------------

            try:
                content = artifact_path.read_text(
                    encoding="utf-8"
                )

            except (
                OSError,
                UnicodeDecodeError,
            ):
                return False

            # ----------------------------------------------
            # Empty artifacts are not valid deliverables.
            # ----------------------------------------------

            if not content.strip():
                return False

            artifact_contents.append(content)

        # --------------------------------------------------
        # If there are no acceptance criteria, the
        # existence of a valid artifact is sufficient.
        # --------------------------------------------------

        if not task.acceptance_criteria:
            return True

        # --------------------------------------------------
        # Combine the actual artifact contents.
        #
        # This allows a task to produce multiple files while
        # still verifying the complete delivered content.
        # --------------------------------------------------

        combined_content = "\n".join(
            artifact_contents
        ).lower()

        # --------------------------------------------------
        # Check 5: Every acceptance criterion must appear
        # in the actual delivered artifact content.
        #
        # Importantly, result.notes is NOT used here.
        # --------------------------------------------------

        for criterion in task.acceptance_criteria:

            if criterion.lower() not in combined_content:
                return False

        return True