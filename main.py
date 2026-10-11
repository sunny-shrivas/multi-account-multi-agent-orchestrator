from pathlib import Path

from account.account_manager import AccountManager
from models.schemas import Task
from orchestrator.master import MasterOrchestrator
from verification.report import DeliveryReport


def build_demo_plan() -> list[Task]:
    return [
        Task(
            task_id="task_001",
            description="Design the authentication service",
            acceptance_criteria=[
                "Define API endpoints",
                "Describe authentication flow",
            ],
        ),
        Task(
            task_id="task_002",
            description="Design the logging service",
            acceptance_criteria=[
                "Define logging structure",
                "Describe error handling",
            ],
        ),
        Task(
            task_id="task_003",
            description="Design the database service",
            acceptance_criteria=[
                "Define database schema",
                "Describe data validation",
            ],
        ),
        Task(
            task_id="task_004",
            description="Design the monitoring service",
            acceptance_criteria=[
                "Define monitoring metrics",
                "Describe alert handling",
            ],
        ),
    ]


def build_demo_account_manager() -> AccountManager:
    """
    Build the Worker pool from the demo YAML configuration.

    The Master does not know how Workers are created.
    AccountManager owns Worker registration and configuration.
    """

    account_manager = AccountManager()

    config_path = (
        Path(__file__).resolve().parent
        / "config"
        / "workers.demo.yaml"
    )

    account_manager.load_from_config(
        config_path=str(config_path)
    )

    return account_manager


def run_demo() -> None:
    print("=" * 70)
    print("MULTI-ACCOUNT MULTI-AGENT ORCHESTRATOR")
    print("DEMO")
    print("=" * 70)

    print("\n[1] Loading Worker accounts from configuration...")

    account_manager = build_demo_account_manager()

    print(
        f"Registered Workers: "
        f"{len(account_manager.workers)}"
    )

    for worker_id, worker in account_manager.workers.items():
        print(
            f"  - {worker_id} "
            f"({type(worker).__name__})"
        )

    print("\n[2] Creating project plan...")

    tasks = build_demo_plan()

    for task in tasks:
        print(
            f"  - {task.task_id}: "
            f"{task.description}"
        )

    print("\n[3] Starting Master Orchestrator...")

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    master.load_plan(tasks)

    print("\n[4] Executing project plan...")
    print("-" * 70)

    master.execute_plan()

    print("-" * 70)

    print("\n[5] Generating final delivery report...")

    report = DeliveryReport(
        tasks=master.tasks,
        results=master.results,
        verification_results=master.verification_results,
    )

    report.print_report()

    print("\n[6] Final Master progress:")

    progress = master.get_progress()

    for key, value in progress.items():
        print(f"  {key}: {value}")

    print("\nDemo completed.")


if __name__ == "__main__":
    run_demo()