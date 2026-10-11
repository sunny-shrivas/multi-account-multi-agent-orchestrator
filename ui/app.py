import json
import sys
from pathlib import Path

import streamlit as st

# ==================================================
# PROJECT ROOT
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ==================================================
# PROJECT IMPORTS
# ==================================================

from account.account_manager import AccountManager
from models.schemas import Task
from orchestrator.master import MasterOrchestrator
from verification.report import DeliveryReport
from workers.failing_mock_worker import FailingMockWorker
from workers.success_mock_worker import SuccessMockWorker
from workers.quota_exceeded_worker import QuotaExceededWorker
from workers.bad_output_mock_worker import BadOutputMockWorker

# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Multi-Account AI Orchestrator",
    page_icon="🤖",
    layout="wide",
)

# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown(
    """
    <style>
        .main { padding-top: 1rem; }
        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
        }
        .worker-card {
            padding: 0.8rem;
            border-radius: 10px;
            border: 1px solid rgba(128, 128, 128, 0.20);
            margin-bottom: 0.5rem;
        }
        .architecture-box {
            padding: 1.2rem;
            border-radius: 12px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .failure-box {
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(255, 80, 80, 0.45);
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# ACCOUNT MANAGERS
# ==================================================


def load_account_manager(mode: str) -> AccountManager:
    """Create the Worker pool for the selected execution mode."""
    account_manager = AccountManager()

    if mode == "Worker Failure":
        account_manager.register_worker(
            FailingMockWorker(worker_id="failure_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_002")
        )
        return account_manager

    if mode == "Quota Exhaustion":
        account_manager.register_worker(
            QuotaExceededWorker(worker_id="quota_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_002")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_003")
        )
        return account_manager

    if mode == "Bad Output Rejection":
        account_manager.register_worker(
            BadOutputMockWorker(worker_id="bad_output_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_001")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_002")
        )
        account_manager.register_worker(
            SuccessMockWorker(worker_id="backup_worker_003")
        )
        return account_manager

    config_path = PROJECT_ROOT / "config" / "workers.demo.yaml"
    account_manager.load_from_config(config_path=str(config_path))
    return account_manager

# ==================================================
# DEFAULT PROJECT PLAN
# ==================================================


def build_default_plan() -> list[Task]:
    """Create four independent tasks for the parallel demo."""
    return [
        Task(
            task_id="task_001",
            description="Design the authentication service",
            dependencies=[],
            acceptance_criteria=[
                "Define API endpoints",
                "Describe authentication flow",
            ],
        ),
        Task(
            task_id="task_002",
            description="Design the logging service",
            dependencies=[],
            acceptance_criteria=[
                "Define logging structure",
                "Describe error handling",
            ],
        ),
        Task(
            task_id="task_003",
            description="Design the database service",
            dependencies=[],
            acceptance_criteria=[
                "Define database schema",
                "Describe data validation",
            ],
        ),
        Task(
            task_id="task_004",
            description="Design the monitoring service",
            dependencies=[],
            acceptance_criteria=[
                "Define monitoring metrics",
                "Describe alert handling",
            ],
        ),
    ]

# ==================================================
# SESSION STATE
# ==================================================

if "project_tasks" not in st.session_state:
    st.session_state.project_tasks = build_default_plan()

if "master" not in st.session_state:
    st.session_state.master = None

if "report" not in st.session_state:
    st.session_state.report = None

if "orchestration_complete" not in st.session_state:
    st.session_state.orchestration_complete = False

if "simulation_mode" not in st.session_state:
    st.session_state.simulation_mode = "Normal"

# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:
    st.title("🤖 Orchestrator")
    st.caption("Multi-Account Multi-Agent Framework")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Workers",
            "Project Plan",
            "Verification",
            "Run Log",
            "Final Report",
        ],
    )

    st.divider()

    st.subheader("🧪 Failure Simulation")
    selected_mode = st.radio(
        "Execution Mode",
        [
            "Normal",
            "Worker Failure",
            "Quota Exhaustion",
            "Bad Output Rejection",
        ],
        index=[
            "Normal",
            "Worker Failure",
            "Quota Exhaustion",
            "Bad Output Rejection",
        ].index(
            st.session_state.simulation_mode
        ),
        help=(
            "Normal runs all success Workers. "
            "Worker Failure simulates a Worker crash. "
            "Quota Exhaustion simulates provider quota exhaustion. "
            "Bad Output Rejection simulates a Worker claiming completion "
            "while producing an invalid deliverable."
        ),
    )

    if selected_mode != st.session_state.simulation_mode:
        st.session_state.simulation_mode = selected_mode
        st.session_state.master = None
        st.session_state.report = None
        st.session_state.orchestration_complete = False
        st.rerun()

    if selected_mode == "Worker Failure":
        st.warning(
            "failure_worker_001 will fail its assigned task. "
            "The Master should reassign that task to a backup Worker."
        )

    if selected_mode == "Quota Exhaustion":
        st.warning(
            "quota_worker_001 will simulate provider quota exhaustion. "
            "The Master should reassign that task to a backup Worker."
        )

    if selected_mode == "Bad Output Rejection":
        st.warning(
            "bad_output_worker_001 will claim completion but produce an invalid "
            "deliverable. The Verification Gate should reject it and the Master "
            "should reassign the task to a backup Worker."
        )

    st.divider()
    st.caption("Take-Home POC")
    st.caption("AI Engineer — GenAI / Agentic AI")

account_manager = load_account_manager(st.session_state.simulation_mode)

# Always show the active Worker pool so the selected execution mode is explicit.

# ==================================================
# HELPER FUNCTIONS
# ==================================================


def get_task_status(task: Task, master: MasterOrchestrator | None) -> tuple[str, str]:
    if master is None:
        return "Pending", "⚪"

    if task.task_id in master.scheduler.completed_tasks:
        return "Verified", "✅"

    if task.task_id in master.scheduler.failed_tasks:
        return "Failed", "❌"

    verification = master.verification_results.get(task.task_id)
    if verification is False:
        return "Rejected", "🔴"

    if task.status == "completed":
        return "Completed", "🟡"

    return "Pending", "⚪"


def get_task_results(task_id: str, master: MasterOrchestrator | None):
    if master is None:
        return []
    return [result for result in master.results if result.task_id == task_id]


def get_latest_task_result(task_id: str, master: MasterOrchestrator | None):
    results = get_task_results(task_id, master)
    return results[-1] if results else None


def calculate_completion_percentage(
    master: MasterOrchestrator | None,
    total_tasks: int,
) -> int:
    if master is None or total_tasks == 0:
        return 0
    verified = len(master.scheduler.completed_tasks)
    return int((verified / total_tasks) * 100)


def render_dependency_chain(tasks: list[Task]) -> None:
    if not tasks:
        st.info("No tasks configured.")
        return

    roots = [task for task in tasks if not task.dependencies]
    dependent_tasks = [task for task in tasks if task.dependencies]

    st.markdown(
        """
        <div class="architecture-box">
            <strong>MASTER ORCHESTRATOR</strong><br>
            ↓<br>
            Dependency-Aware Scheduler<br>
            ↓<br>
            Worker Pool<br>
            ↓<br>
            Verification Gate
        </div>
        """,
        unsafe_allow_html=True,
    )

    if roots:
        st.write("**Ready / Independent Tasks**")
        columns = st.columns(min(len(roots), 4))
        for index, task in enumerate(roots):
            with columns[index % len(columns)]:
                st.info(f"**{task.task_id}**\n\n{task.description}")

    if dependent_tasks:
        st.write("**Dependency-Aware Tasks**")
        for task in dependent_tasks:
            dependencies = ", ".join(task.dependencies)
            st.warning(
                f"**{task.task_id}** depends on `{dependencies}`"
            )


def render_worker_pool() -> None:
    total_workers = len(account_manager.workers)
    columns = st.columns(min(max(total_workers, 1), 4))

    for index, (worker_id, worker) in enumerate(account_manager.workers.items()):
        with columns[index % len(columns)]:
            is_busy = worker_id in account_manager.busy_workers
            status = "🔴 BUSY" if is_busy else "🟢 AVAILABLE"
            st.markdown(
                f"""
                <div class="worker-card">
                    <strong>{worker_id}</strong><br>
                    <span>{type(worker).__name__}</span><br>
                    <span>{status}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ==================================================
# DASHBOARD
# ==================================================

if page == "Dashboard":
    st.title("🤖 Multi-Account AI Orchestrator")
    st.write(
        "Coordinate multiple AI Workers through a Master Orchestrator "
        "with dependency-aware scheduling, verification, and failure recovery."
    )

    if st.session_state.simulation_mode == "Worker Failure":
        st.markdown(
            """
            <div class="failure-box">
                <strong>🧪 Worker Failure Simulation Active</strong><br>
                One Worker will fail. The Master must detect the failure,
                reassign the task, and verify the backup Worker output.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.simulation_mode == "Quota Exhaustion":
        st.markdown(
            """
            <div class="failure-box">
                <strong>🧪 Quota Exhaustion Simulation Active</strong><br>
                One Worker will simulate provider quota exhaustion.
                The Master must detect the failure, reassign the task,
                and verify the backup Worker output.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.session_state.simulation_mode == "Bad Output Rejection":
        st.markdown(
            """
            <div class="failure-box">
                <strong>🧪 Bad Output Rejection Simulation Active</strong><br>
                One Worker will claim completion but produce an invalid deliverable.
                The Verification Gate must reject the output, after which the Master
                reassigns the task and verifies the backup Worker output.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    master = st.session_state.master
    total_workers = len(account_manager.workers)
    available_workers = len(account_manager.get_available_workers())
    busy_workers = total_workers - available_workers

    if master is not None:
        progress = master.get_progress()
        total_tasks = progress["total_tasks"]
        completed_tasks = progress["completed_tasks"]
        verified_tasks = progress["verified_tasks"]
        failed_tasks = progress["failed_tasks"]
        rejected_tasks = progress["rejected_tasks"]
    else:
        total_tasks = len(st.session_state.project_tasks)
        completed_tasks = 0
        verified_tasks = 0
        failed_tasks = 0
        rejected_tasks = 0

    completion_percentage = calculate_completion_percentage(master, total_tasks)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Workers", total_workers)
    with col2:
        st.metric(
            "Available",
            available_workers,
            delta=f"{busy_workers} busy" if busy_workers else None,
        )
    with col3:
        st.metric("Tasks", total_tasks)
    with col4:
        st.metric("Verified", verified_tasks)
    with col5:
        st.metric("Completion", f"{completion_percentage}%")

    st.progress(
        completion_percentage / 100 if total_tasks > 0 else 0,
        text=f"Project completion: {completion_percentage}%",
    )

    st.divider()
    st.subheader("⚡ Worker Pool")
    st.caption(
        "Workers are independently scheduled by the Master and can execute tasks in parallel."
    )
    render_worker_pool()

    st.divider()
    st.subheader("🧠 Orchestration Flow")
    flow_col1, flow_col2, flow_col3, flow_col4 = st.columns(4)

    with flow_col1:
        st.markdown(
            """
            <div class="architecture-box">
                📋<br><strong>1. Project Plan</strong><br>Tasks + dependencies
            </div>
            """,
            unsafe_allow_html=True,
        )
    with flow_col2:
        st.markdown(
            """
            <div class="architecture-box">
                🧠<br><strong>2. Master</strong><br>Schedule + govern
            </div>
            """,
            unsafe_allow_html=True,
        )
    with flow_col3:
        st.markdown(
            """
            <div class="architecture-box">
                ⚡<br><strong>3. Workers</strong><br>Parallel execution
            </div>
            """,
            unsafe_allow_html=True,
        )
    with flow_col4:
        st.markdown(
            """
            <div class="architecture-box">
                ✅<br><strong>4. Verification</strong><br>Accept or reject
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("🔗 Task Dependency Graph")
    render_dependency_chain(st.session_state.project_tasks)

    st.divider()
    st.subheader("▶ Run Orchestration")
    st.write(
        "The Master executes all ready tasks in parallel while respecting dependencies. "
        "A task becomes complete only after passing the Verification Gate."
    )

    if st.button(
        "▶ Start Orchestration",
        type="primary",
        use_container_width=True,
    ):
        tasks = st.session_state.project_tasks

        if not tasks:
            st.error("No project tasks are configured.")
        else:
            # A Task object is updated to completed by the Master after verification.
            # Reset task runtime state before every new orchestration run so the same
            # project plan can be executed again in a different simulation mode.
            for task in tasks:
                task.status = "pending"
                task.assigned_worker = None

            st.session_state.orchestration_complete = False
            progress_bar = st.progress(0, text="Initializing Master Orchestrator...")

            try:
                master = MasterOrchestrator(account_manager=account_manager)

                progress_bar.progress(20, text="Loading project plan...")
                master.load_plan(tasks)

                progress_bar.progress(40, text="Building dependency graph...")
                progress_bar.progress(60, text="Executing tasks across available Workers...")
                master.execute_plan()

                progress_bar.progress(80, text="Running Verification Gate...")

                report = DeliveryReport(
                    tasks=master.tasks,
                    results=master.results,
                    verification_results=master.verification_results,
                )

                st.session_state.master = master
                st.session_state.report = report
                st.session_state.orchestration_complete = True

                progress_bar.progress(100, text="Orchestration completed.")
                st.success("Master Orchestrator completed the dependency-aware project plan.")

            except Exception as exc:
                progress_bar.empty()
                st.error("Orchestration failed.")
                st.exception(exc)

    # --------------------------------------------------
    # EXECUTION RESULTS
    # --------------------------------------------------

    if st.session_state.orchestration_complete:
        st.divider()
        st.subheader("📊 Execution Results")

        master = st.session_state.master
        progress = master.get_progress()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total", progress["total_tasks"])
        with col2:
            st.metric("Completed", progress["completed_tasks"])
        with col3:
            st.metric("Verified", progress["verified_tasks"])
        with col4:
            st.metric("Rejected", progress["rejected_tasks"])
        with col5:
            st.metric("Failed", progress["failed_tasks"])

        if (
            progress["verified_tasks"] == progress["total_tasks"]
            and progress["total_tasks"] > 0
        ):
            st.success("✅ All tasks passed the Verification Gate.")
        else:
            st.warning("⚠️ Not all tasks passed verification.")

        st.subheader("Task Execution Status")
        for task in master.tasks:
            status, emoji = get_task_status(task, master)
            results = get_task_results(task.task_id, master)
            latest_result = results[-1] if results else None
            assigned_worker = (
                latest_result.worker_id if latest_result is not None else "Not assigned"
            )

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 4, 2, 2])
                with col1:
                    st.write(f"**{emoji} {task.task_id}**")
                with col2:
                    st.write(task.description)
                with col3:
                    st.write(f"**Status:** {status}")
                with col4:
                    st.write(f"**Worker:** {assigned_worker}")

                if latest_result is not None:
                    st.caption(
                        f"Attempts: {len(results)} | Artifacts changed: "
                        f"{len(latest_result.files_changed)}"
                    )

                if len(results) > 1:
                    st.info(
                        "🔁 Master reassigned this task after an earlier Worker result failed."
                    )
                    for attempt_index, result in enumerate(results, start=1):
                        st.caption(
                            f"Attempt {attempt_index}: {result.worker_id} → "
                            f"{result.status}"
                            + (f" ({result.error})" if result.error else "")
                        )

# ==================================================
# WORKERS PAGE
# ==================================================

elif page == "Workers":
    st.title("👥 Worker Accounts")
    st.write("Workers registered through the Account Manager.")
    st.divider()

    if st.session_state.simulation_mode == "Worker Failure":
        st.warning(
            "Failure simulation: failure_worker_001 is intentionally configured "
            "to fail, while backup Workers are available for reassignment."
        )

    if st.session_state.simulation_mode == "Quota Exhaustion":
        st.warning(
            "Quota simulation: quota_worker_001 is intentionally configured "
            "to report QUOTA_EXHAUSTED, while backup Workers are available "
            "for reassignment."
        )

    if st.session_state.simulation_mode == "Bad Output Rejection":
        st.warning(
            "Bad output simulation: bad_output_worker_001 is intentionally configured "
            "to report completion with an invalid deliverable, while backup Workers "
            "are available for reassignment after Verification Gate rejection."
        )

    for worker_id, worker in account_manager.workers.items():
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(worker_id)
                st.write(f"**Implementation:** {type(worker).__name__}")
                st.write(f"**Workspace:** `workspaces/{worker_id}`")
            with col2:
                if worker_id in account_manager.busy_workers:
                    st.error("🔴 BUSY")
                else:
                    st.success("🟢 AVAILABLE")

# ==================================================
# PROJECT PLAN PAGE
# ==================================================

elif page == "Project Plan":
    st.title("📋 Project Plan")
    st.write("Create tasks and define their dependencies.")
    st.divider()

    st.subheader("Current Tasks")

    if not st.session_state.project_tasks:
        st.info("No tasks have been added.")
    else:
        for index, task in enumerate(st.session_state.project_tasks):
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### {task.task_id}")
                    st.write(task.description)

                    if task.dependencies:
                        st.write("**Depends On:**")
                        for dependency in task.dependencies:
                            st.write(f"• {dependency}")
                    else:
                        st.write("**Depends On:** None")

                    st.write("**Acceptance Criteria:**")
                    if task.acceptance_criteria:
                        for criterion in task.acceptance_criteria:
                            st.write(f"• {criterion}")
                    else:
                        st.caption("No acceptance criteria defined.")

                with col2:
                    if st.button("🗑️ Remove", key=f"remove_task_{index}"):
                        st.session_state.project_tasks.pop(index)
                        st.session_state.master = None
                        st.session_state.report = None
                        st.session_state.orchestration_complete = False
                        st.rerun()

    st.divider()
    st.subheader("➕ Add New Task")

    existing_task_ids = [
        task.task_id for task in st.session_state.project_tasks
    ]

    with st.form("add_task_form", clear_on_submit=True):
        task_description = st.text_input(
            "Task Description",
            placeholder="Example: Design the payment service",
        )
        acceptance_criteria_text = st.text_area(
            "Acceptance Criteria",
            placeholder=(
                "Enter one criterion per line.\n"
                "Example:\n"
                "Define payment API\n"
                "Describe payment validation"
            ),
            height=150,
        )
        dependencies = st.multiselect(
            "Depends On",
            options=existing_task_ids,
            help=(
                "The selected tasks must be successfully completed and verified "
                "before this task becomes ready."
            ),
        )
        add_task = st.form_submit_button(
            "➕ Add Task",
            use_container_width=True,
        )

    if add_task:
        if not task_description.strip():
            st.error("Task description cannot be empty.")
        else:
            criteria = [
                line.strip()
                for line in acceptance_criteria_text.splitlines()
                if line.strip()
            ]
            next_number = len(st.session_state.project_tasks) + 1
            new_task = Task(
                task_id=f"task_{next_number:03d}",
                description=task_description.strip(),
                dependencies=dependencies,
                acceptance_criteria=criteria,
            )
            st.session_state.project_tasks.append(new_task)
            st.session_state.master = None
            st.session_state.report = None
            st.session_state.orchestration_complete = False
            st.success(f"Added {new_task.task_id}.")
            st.rerun()

# ==================================================
# VERIFICATION PAGE
# ==================================================

elif page == "Verification":
    st.title("✅ Verification Gate")
    st.write(
        "Every Worker result must pass the Verification Gate before the Master considers the task complete."
    )

    master = st.session_state.master
    if master is None:
        st.info("Run the orchestration first to see verification results.")
    else:
        progress = master.get_progress()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Verified", progress["verified_tasks"])
        with col2:
            st.metric("Rejected", progress["rejected_tasks"])
        with col3:
            st.metric("Failed", progress["failed_tasks"])

        st.divider()

        for task in master.tasks:
            verification = master.verification_results.get(task.task_id)
            results = get_task_results(task.task_id, master)

            if verification is True:
                st.success(f"✅ {task.task_id}: PASS")
            elif verification is False:
                st.error(f"❌ {task.task_id}: FAIL")
            else:
                st.info(f"⚪ {task.task_id}: NOT VERIFIED")

            if results:
                with st.expander(f"Worker attempts — {task.task_id}"):
                    for attempt_index, result in enumerate(results, start=1):
                        st.write(f"### Attempt {attempt_index}")
                        st.write(f"**Worker:** {result.worker_id}")
                        st.write(f"**Status:** {result.status}")

                        st.write("**Files Changed:**")
                        if result.files_changed:
                            for file_name in result.files_changed:
                                st.write(f"• `{file_name}`")
                        else:
                            st.write("No files reported.")

                        st.write("**Notes:**")
                        st.write(result.notes or "No notes.")

                        if result.error:
                            st.error(f"Error: {result.error}")

                        if attempt_index < len(results):
                            st.divider()

# ==================================================
# RUN LOG PAGE
# ==================================================

elif page == "Run Log":
    st.title("📜 Run Log")
    st.write("Execution events recorded by the Master Orchestrator.")
    st.divider()

    log_path = PROJECT_ROOT / "run.log"

    if not log_path.exists():
        st.info("No orchestration events have been logged yet.")
    else:
        try:
            with log_path.open("r", encoding="utf-8") as log_file:
                log_lines = [line.strip() for line in log_file if line.strip()]

            st.metric("Recorded Events", len(log_lines))
            st.divider()

            for line in reversed(log_lines):
                try:
                    event = json.loads(line)
                    event_name = event.get("event", "UNKNOWN")
                    timestamp = event.get("timestamp", "")
                    task_id = event.get("task_id")
                    worker_id = event.get("worker_id")
                    details = event.get("details", {})

                    title_parts = [event_name]
                    if task_id:
                        title_parts.append(task_id)
                    if worker_id:
                        title_parts.append(worker_id)

                    with st.expander(" | ".join(title_parts)):
                        st.caption(timestamp)
                        if task_id:
                            st.write(f"**Task:** {task_id}")
                        if worker_id:
                            st.write(f"**Worker:** {worker_id}")
                        if details:
                            st.json(details)
                except Exception:
                    st.code(line)

        except Exception as exc:
            st.error("Unable to read the run log.")
            st.exception(exc)

# ==================================================
# FINAL REPORT PAGE
# ==================================================

elif page == "Final Report":
    st.title("📄 Final Delivery Report")

    report = st.session_state.report
    master = st.session_state.master

    if report is None or master is None:
        st.info("Run the orchestration first to generate the final delivery report.")
    else:
        progress = master.get_progress()
        total_tasks = progress["total_tasks"]
        verified_tasks = progress["verified_tasks"]
        failed_tasks = progress["failed_tasks"]
        rejected_tasks = progress["rejected_tasks"]

        if verified_tasks == total_tasks and total_tasks > 0:
            overall_status = "COMPLETED"
        elif verified_tasks > 0:
            overall_status = "PARTIALLY_COMPLETED"
        elif total_tasks == 0:
            overall_status = "NO_TASKS"
        else:
            overall_status = "FAILED"

        st.subheader("Overall Status")
        if overall_status == "COMPLETED":
            st.success(f"✅ {overall_status}")
        elif overall_status == "PARTIALLY_COMPLETED":
            st.warning(f"⚠️ {overall_status}")
        else:
            st.error(f"❌ {overall_status}")

        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tasks", total_tasks)
        with col2:
            st.metric("Verified", verified_tasks)
        with col3:
            st.metric("Rejected", rejected_tasks)
        with col4:
            st.metric("Failed", failed_tasks)

        st.divider()
        st.subheader("Plan vs Delivered")

        for task in master.tasks:
            results = get_task_results(task.task_id, master)
            result = results[-1] if results else None
            verification = master.verification_results.get(task.task_id)
            status, emoji = get_task_status(task, master)

            with st.container(border=True):
                st.markdown(f"### {emoji} {task.task_id}")
                st.write(f"**Planned Task:** {task.description}")
                st.write(f"**Status:** {status}")

                if task.dependencies:
                    st.write(
                        f"**Dependencies:** {', '.join(task.dependencies)}"
                    )

                if task.acceptance_criteria:
                    st.write("**Acceptance Criteria:**")
                    for criterion in task.acceptance_criteria:
                        st.write(f"• {criterion}")

                if result is not None:
                    st.write(f"**Delivered By:** {result.worker_id}")
                    st.write("**Files Changed:**")
                    if result.files_changed:
                        for file_name in result.files_changed:
                            st.write(f"• `{file_name}`")
                    else:
                        st.write("No files reported.")

                    if result.notes:
                        st.write(f"**Worker Notes:** {result.notes}")
                    if result.error:
                        st.error(f"Worker Error: {result.error}")
                else:
                    st.write("**Delivery:** No Worker result recorded.")

                if verification is True:
                    st.success("Verification Gate: PASS")
                elif verification is False:
                    st.error("Verification Gate: FAIL")
                else:
                    st.warning("Verification Gate: NOT RUN")

        st.divider()
        st.subheader("Architecture Summary")
        st.markdown(
            """
            **Master Orchestrator**

            The Master owns planning, scheduling, dependency management and the final completion decision.

            **Worker Pool**

            Each Worker has an isolated workspace and executes an assigned task independently.

            **Dependency Scheduler**

            Independent tasks can run concurrently. Dependent tasks remain blocked until all required dependencies have been successfully verified.

            **Verification Gate**

            Worker completion does not automatically mean task completion. The Master checks the Worker output against the task acceptance criteria before marking the task complete.

            **Failure Recovery**

            Failed or rejected work can be retried using another available Worker.
            """
        )
