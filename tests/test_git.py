"""Tests for git module."""

import subprocess
from pathlib import Path
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
        check=True
    )


def test_run_git_command_error(mock_run):
    """Test handling git command errors."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git status", stderr="fatal: not a git repository"
    )
    
    with pytest.raises(git.GitError, match="Git command failed: fatal: not a git repository"):
        git.run_git_command(["status"])


def test_run_git_command_silent_error(mock_run):
    """Test silent error handling."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git status", stderr="fatal: not a git repository"
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
        check=False
    )


def test_is_not_git_repo(mock_run):
    """Test non-git repository detection."""
    cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    mock_run.side_effect = subprocess.CalledProcessError(
        128, cmd, stderr="fatal: not a git repository"
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
* master
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
        check=True
    )


def test_delete_branch_force(mock_run):
    """Test forced branch deletion."""
    git.delete_branch("feature/123", force=True)
    mock_run.assert_called_once_with(
        ["git", "branch", "-D", "feature/123"],
        capture_output=True,
        text=True,
        check=True
    )


def test_optimize_repo(mock_run):
    """Test repository optimization."""
    with patch("pathlib.Path.unlink") as mock_unlink:
        git.optimize_repo()
        
        # Should try to remove gc.log
        mock_unlink.assert_called_once()
        
        # Should run git prune and gc
        assert mock_run.call_count == 2
        mock_run.assert_any_call(
            ["git", "prune"],
            capture_output=True,
            text=True,
            check=True
        )
        mock_run.assert_any_call(
            ["git", "gc"],
            capture_output=True,
            text=True,
            check=True
        )


def test_fetch_and_prune(mock_run):
    """Test fetch and prune operation."""
    git.fetch_and_prune()
    mock_run.assert_called_once_with(
        ["git", "fetch", "-p"],
        capture_output=True,
        text=True,
        check=True
    )


def test_filter_protected_branches():
    """Test filtering protected branches."""
    branches = ["main", "develop", "feature/123"]
    protected = ["main", "master"]
    
    filtered = git.filter_protected_branches(branches, protected)
    assert filtered == ["develop", "feature/123"]
