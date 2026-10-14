from pathlib import Path

from account.account_manager import AccountManager
from orchestrator.master import MasterOrchestrator
from verification.report import DeliveryReport


def build_demo_account_manager() -> AccountManager:
    """
    Build the Worker pool from the demo YAML configuration.
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


def build_demo_project_plan() -> str:
    """
    Return a written project plan for demonstration.
    """
    return """
    1. Design the authentication service
    2. Design the logging service
    3. Design the database service
    4. Design the monitoring service
    """


def run_demo() -> None:
    print("=" * 70)
    print("MULTI-ACCOUNT MULTI-AGENT ORCHESTRATOR")
    print("PLAN DECOMPOSITION DEMO")
    print("=" * 70)

    print("\n[1] Loading Worker accounts from configuration...")

    account_manager = build_demo_account_manager()

    print(f"Registered Workers: {len(account_manager.workers)}")

    for worker_id, worker in account_manager.workers.items():
        print(f"  - {worker_id} ({type(worker).__name__})")

    print("\n[2] Ingesting written project plan...")

    project_plan = build_demo_project_plan()
    print(project_plan.strip())

    print("\n[3] Decomposing plan into structured tasks...")

    master = MasterOrchestrator(
        account_manager=account_manager
    )

    acceptance_criteria = {
        "task_001": [
            "Define API endpoints",
            "Describe authentication flow",
        ],
        "task_002": [
            "Define logging structure",
            "Describe error handling",
        ],
        "task_003": [
            "Define database schema",
            "Describe data validation",
        ],
        "task_004": [
            "Define monitoring metrics",
            "Describe alert handling",
        ],
    }

    dependencies = {
        "task_002": ["task_001"],
        "task_003": ["task_001"],
        "task_004": ["task_002", "task_003"],
    }

    tasks = master.load_plan_from_text(
        project_plan,
        acceptance_criteria=acceptance_criteria,
        dependencies=dependencies,
    )

    for task in tasks:
        dependency_text = (
            ", ".join(task.dependencies)
            if task.dependencies
            else "None"
        )

        print(f"\n  Task: {task.task_id}")
        print(f"  Description: {task.description}")
        print(f"  Dependencies: {dependency_text}")
        print("  Acceptance criteria:")

        for criterion in task.acceptance_criteria:
            print(f"    - {criterion}")

    print("\n[4] Executing dependency-aware project plan...")
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

    for key, value in master.get_progress().items():
        print(f"  {key}: {value}")

    print("\nDemo completed.")


if __name__ == "__main__":
    run_demo()
