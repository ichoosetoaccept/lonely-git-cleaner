"""Tests for git module."""

import subprocess
from unittest.mock import patch

import pytest
from git_cleanup import git


@pytest.fixture
def mock_run():
    """Fixture to mock subprocess.run."""
    with patch("subprocess.run") as mock:
        mock.return_value.stdout = ""
        mock.return_value.stderr = ""
        yield mock


def test_run_git_command(mock_run):
    """Test running git commands."""
    git.run_git_command(["status"])
    mock_run.assert_called_once_with(
        ["git", "status"],
        capture_output=True,
        text=True,
        check=True,
    )


def test_run_git_command_error(mock_run):
    """Test handling git command errors."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        "git status",
        stderr="fatal: not a git repository",
    )

    with pytest.raises(
        git.GitError,
        match="Git command failed: fatal: not a git repository",
    ):
        git.run_git_command(["status"])


def test_run_git_command_silent_error(mock_run):
    """Test silent error handling."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1,
        "git status",
        stderr="fatal: not a git repository",
    )

    stdout, stderr = git.run_git_command(["status"], silent=True)
    assert stdout == ""
    assert stderr == "fatal: not a git repository"


def test_is_git_repo(mock_run):
    """Test git repository detection."""
    mock_run.return_value.stdout = "true"
    mock_run.return_value.stderr = ""
    assert git.is_git_repo()
    mock_run.assert_called_once_with(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_is_not_git_repo(mock_run):
    """Test non-git repository detection."""
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    mock_run.side_effect = subprocess.CalledProcessError(
        128,
        cmd,
        stderr="fatal: not a git repository",
    )
    assert not git.is_git_repo()


def test_get_gone_branches(mock_run):
    """Test detecting branches with gone remotes."""
    mock_run.return_value.stdout = """
  feature/123 abcd123 [origin/feature/123: gone]
  develop    efgh456 [origin/develop]
  main       ijkl789 [origin/main]
"""
    branches = git.get_gone_branches()
    assert branches == ["feature/123"]


def test_get_merged_branches(mock_run):
    """Test detecting merged branches."""
    mock_run.return_value.stdout = """
  feature/456
  hotfix/789
* main
"""
    branches = git.get_merged_branches()
    assert set(branches) == {"feature/456", "hotfix/789"}


def test_delete_branch(mock_run):
    """Test branch deletion."""
    git.delete_branch("feature/123")
    mock_run.assert_called_once_with(
        ["git", "branch", "-d", "feature/123"],
        capture_output=True,
        text=True,
        check=True,
    )


def test_delete_branch_force(mock_run):
    """Test forced branch deletion."""
    git.delete_branch("feature/123", force=True)
    mock_run.assert_called_once_with(
        ["git", "branch", "-D", "feature/123"],
        capture_output=True,
        text=True,
        check=True,
    )


def test_delete_branch_with_special_chars(mock_run):
    """Test branch deletion with special characters."""
    git.delete_branch("feature/*123")
    mock_run.assert_called_once_with(
        ["git", "branch", "-d", "feature/\\*123"],
        capture_output=True,
        text=True,
        check=True,
    )


EXPECTED_GIT_COMMANDS = 2  # prune and gc commands


def test_optimize_repo(mock_run):
    """Test repository optimization."""
    with patch("pathlib.Path.unlink") as mock_unlink:
        git.optimize_repo()

        # Should try to remove gc.log
        mock_unlink.assert_called_once()

        # Should run git prune and gc
        assert mock_run.call_count == EXPECTED_GIT_COMMANDS
        mock_run.assert_any_call(
            ["git", "prune"],
            capture_output=True,
            text=True,
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "gc"],
            capture_output=True,
            text=True,
            check=True,
        )


def test_optimize_repo_unlink_error(mock_run):
    """Test repository optimization when gc.log unlink fails."""
    with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
        git.optimize_repo()  # Should handle the error gracefully

        # Should still run git commands despite unlink error
        assert mock_run.call_count == EXPECTED_GIT_COMMANDS
        mock_run.assert_any_call(
            ["git", "prune"],
            capture_output=True,
            text=True,
            check=True,
        )
        mock_run.assert_any_call(
            ["git", "gc"],
            capture_output=True,
            text=True,
            check=True,
        )


def test_fetch_and_prune(mock_run):
    """Test fetch and prune operation."""
    git.fetch_and_prune()
    mock_run.assert_called_once_with(
        ["git", "fetch", "-p"],
        capture_output=True,
        text=True,
        check=True,
    )


def test_filter_protected_branches():
    """Test filtering protected branches."""
    branches = ["main", "develop", "feature/123"]
    protected = ["main"]

    filtered = git.filter_protected_branches(branches, protected)
    assert filtered == ["develop", "feature/123"]


def test_get_merged_remote_branches(mocker):
    """Test getting merged remote branches."""
    # Mock the current branch
    mocker.patch(
        "git_cleanup.git.run_git_command",
        side_effect=[
            ("main", ""),  # Current branch
            (
                "origin/feature-1\n" "origin/feature-2\n" "origin/main\n" "origin/dev",
                "",
            ),  # Remote branches
        ],
    )

    result = git.get_merged_remote_branches()
    assert result == ["feature-1", "feature-2", "dev"]
    git.run_git_command.assert_has_calls(
        [
            mocker.call(["rev-parse", "--abbrev-ref", "HEAD"]),
            mocker.call(["branch", "-r", "--merged"]),
        ],
    )


def test_get_merged_remote_branches_empty(mocker):
    """Test getting merged remote branches when none exist."""
    mocker.patch(
        "git_cleanup.git.run_git_command",
        side_effect=[
            ("main", ""),  # Current branch
            ("", ""),  # No remote branches
        ],
    )

    result = git.get_merged_remote_branches()
    assert result == []


def test_get_merged_remote_branches_with_current(mocker):
    """Test getting merged remote branches with current branch remote."""
    mocker.patch(
        "git_cleanup.git.run_git_command",
        side_effect=[
            ("feature-1", ""),  # Current branch
            (
                "origin/feature-1\n"  # Should be skipped
                "origin/feature-2\n"
                "origin/main",
                "",
            ),
        ],
    )

    result = git.get_merged_remote_branches()
    assert result == ["feature-2", "main"]


def test_delete_remote_branch(mocker):
    """Test deleting a remote branch."""
    mock_run = mocker.patch("git_cleanup.git.run_git_command")
    git.delete_remote_branch("feature-1")
    mock_run.assert_called_once_with(["push", "origin", "--delete", "feature-1"])


def test_delete_remote_branch_error(mocker):
    """Test error handling when deleting a remote branch."""
    mocker.patch(
        "git_cleanup.git.run_git_command",
        side_effect=git.GitError("Remote branch deletion failed"),
    )

    with pytest.raises(git.GitError, match="Remote branch deletion failed"):
        git.delete_remote_branch("feature-1")


def test_get_gone_branches_complex_output(mock_run):
    """Test detecting branches with gone remotes with complex output."""
    mock_run.return_value.stdout = """
  feature/123 abcd123 [origin/feature/123: gone] some extra info
* current-branch def456 [origin/current-branch: gone] other info
  develop    efgh456 [origin/develop]
  main       ijkl789 [origin/main]
  no-remote  mnop123
"""
    branches = git.get_gone_branches()
    assert set(branches) == {"feature/123", "current-branch"}
