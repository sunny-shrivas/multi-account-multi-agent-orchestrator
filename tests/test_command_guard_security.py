import pytest

from security.command_guard import CommandGuard


def test_blocks_rm_rf():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("rm -rf /tmp/project")


def test_blocks_force_push():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("git push --force origin main")


def test_blocks_force_push_short_form():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("git push -f origin main")


def test_blocks_hard_reset():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("git reset --hard HEAD~1")


def test_blocks_git_clean():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("git clean -fd")


def test_blocks_docker_prune():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("docker system prune")


def test_blocks_kubectl_delete():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("kubectl delete deployment app")


def test_blocks_terraform_destroy():
    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate("terraform destroy")


def test_allows_safe_command():
    guard = CommandGuard()

    guard.validate("git status")


def test_allows_safe_python_command():
    guard = CommandGuard()

    guard.validate("python main.py")