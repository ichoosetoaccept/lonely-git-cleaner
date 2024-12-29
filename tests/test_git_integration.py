"""Integration tests for Git operations."""

import os
from pathlib import Path

import pytest
from arborist.cli import app
from typer.testing import CliRunner

from tests.git_test_env import GitHubTestEnvironment


@pytest.fixture
def git_env(tmp_path):
    """Create a test Git environment."""
    # Create and set up test environment
    env = GitHubTestEnvironment()
    env.setup()

    # Save current directory
    os.chdir(tmp_path)  # Change to a temporary directory first
    cwd = Path.cwd()

    # Change to test repo
    os.chdir(env.repo_dir)

    yield env

    # Clean up and restore directory
    try:
        os.chdir(cwd)
    except (FileNotFoundError, OSError):
        pass  # Ignore errors when changing back to original directory
    env.cleanup()


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


def test_cleanup_merged_branches(git_env, runner, monkeypatch):
    """Test cleaning up merged branches with real Git operations."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and push a feature branch
    git_env.create_branch("feature/test", "feature")

    # Merge the feature branch
    git_env.merge_branch("feature/test", "main")

    # Run our cleanup tool
    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0

    # Verify the branch was cleaned up
    branches = git_env.get_branches()
    assert "feature/test" not in branches
    assert "main" in branches


def test_cleanup_gone_branches(git_env, runner, monkeypatch):
    """Test cleaning up branches with deleted remotes."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and push a feature branch
    git_env.create_branch("feature/gone", "gone")

    # Delete the remote branch
    git_env.delete_remote_branch("feature/gone")

    # Debug: Show branch status
    print("\nBefore cleanup:")
    git_env._run_git("branch", "-vv")

    # Run our cleanup tool
    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0

    # Verify the branch was cleaned up
    branches = git_env.get_branches()
    assert "feature/gone" not in branches
    assert "main" in branches


def test_protect_branches(git_env, runner, monkeypatch):
    """Test that protected branches are not deleted."""
    monkeypatch.chdir(git_env.repo_dir)

    # Switch to main branch
    git_env.switch_branch("main")

    # Create and push protected branches
    git_env.create_branch("develop", "develop")
    git_env.create_branch("staging", "staging")

    # Create and push a feature branch
    git_env.create_branch("feature/test", "feature")

    # Merge all branches to main
    git_env.merge_branch("develop", "main")
    git_env.merge_branch("staging", "main")
    git_env.merge_branch("feature/test", "main")

    # Run our cleanup tool with protection
    result = runner.invoke(
        app,
        ["--no-interactive", "--protect", "develop", "--protect", "staging"],
    )
    assert result.exit_code == 0

    # Verify protected branches still exist
    branches = git_env.get_branches()
    assert "develop" in branches
    assert "staging" in branches
    assert "feature/test" not in branches
    assert "main" in branches
