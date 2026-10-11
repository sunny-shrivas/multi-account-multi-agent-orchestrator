import pytest

from security.command_guard import CommandGuard


def test_safe_command_is_allowed():
    """
    Normal development commands should be allowed.
    """

    guard = CommandGuard()

    assert guard.is_allowed(
        "python main.py"
    )

    assert guard.is_allowed(
        "pytest -q"
    )

    assert guard.is_allowed(
        "git status"
    )

    assert guard.is_allowed(
        "git add ."
    )


def test_rm_rf_is_blocked():
    """
    Recursive force deletion must be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "rm -rf /tmp/project"
    )


def test_force_push_is_blocked():
    """
    Force pushing must be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "git push --force origin main"
    )


def test_short_force_push_is_blocked():
    """
    The short force-push form must also be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "git push -f origin main"
    )


def test_git_reset_hard_is_blocked():
    """
    Hard Git reset can destroy local changes and must
    therefore be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "git reset --hard HEAD~1"
    )


def test_git_clean_is_blocked():
    """
    git clean -fd can permanently remove untracked files
    and directories, so it must be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "git clean -fd"
    )


def test_docker_system_prune_is_blocked():
    """
    Docker system prune can remove Docker resources and
    therefore must be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "docker system prune"
    )


def test_kubectl_delete_is_blocked():
    """
    Kubernetes deletion commands must be blocked.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "kubectl delete pod test-pod"
    )


def test_terraform_destroy_is_blocked():
    """
    Terraform destroy must be blocked because it can
    destroy infrastructure.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "terraform destroy"
    )


def test_dangerous_commands_raise_error():
    """
    validate() must raise an exception for blocked commands.
    """

    guard = CommandGuard()

    with pytest.raises(ValueError):
        guard.validate(
            "git reset --hard HEAD~1"
        )

    with pytest.raises(ValueError):
        guard.validate(
            "terraform destroy"
        )

    with pytest.raises(ValueError):
        guard.validate(
            "rm -rf /tmp/project"
        )


def test_safe_command_does_not_raise_error():
    """
    Safe commands should pass validation.
    """

    guard = CommandGuard()

    guard.validate(
        "pytest -q"
    )


def test_command_with_extra_whitespace_is_still_blocked():
    """
    Command normalization should prevent simple whitespace
    variations from bypassing the guard.
    """

    guard = CommandGuard()

    assert not guard.is_allowed(
        "git   push   --force   origin   main"
    )


if __name__ == "__main__":
    test_safe_command_is_allowed()
    test_rm_rf_is_blocked()
    test_force_push_is_blocked()
    test_short_force_push_is_blocked()
    test_git_reset_hard_is_blocked()
    test_git_clean_is_blocked()
    test_docker_system_prune_is_blocked()
    test_kubectl_delete_is_blocked()
    test_terraform_destroy_is_blocked()
    test_dangerous_commands_raise_error()
    test_safe_command_does_not_raise_error()
    test_command_with_extra_whitespace_is_still_blocked()

    print(
        "\nAll command guard tests passed."
    )