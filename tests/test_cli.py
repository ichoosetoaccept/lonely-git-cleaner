"""Tests for command-line interface."""

import pytest
from arborist.cli import app
from typer.testing import CliRunner

from tests.git_test_env import GitHubTestEnvironment


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def git_env():
    """Create a Git test environment."""
    env = GitHubTestEnvironment()
    env.setup()
    yield env
    env.cleanup()


def test_main_not_git_repo(runner, tmp_path, monkeypatch):
    """Test running in a non-git directory."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Not in a git repository" in result.stdout


def test_main_no_branches(runner, git_env, monkeypatch):
    """Test running with no branches to clean."""
    monkeypatch.chdir(git_env.repo_dir)
    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0
    assert "No branches with gone remotes found" in result.stdout.replace("\n", " ")


def test_main_with_gone_branches(runner, git_env, monkeypatch):
    """Test cleaning up gone branches."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete a branch
    git_env.create_branch("feature/test", "Test feature branch")
    git_env.delete_remote_branch("feature/test")

    result = runner.invoke(app, ["--no-interactive"])
    assert result.exit_code == 0
    assert "feature/test" in result.stdout


def test_main_dry_run(runner, git_env, monkeypatch):
    """Test dry run mode."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete a branch
    git_env.create_branch("feature/test", "Test feature branch")
    git_env.delete_remote_branch("feature/test")

    result = runner.invoke(app, ["--dry-run", "--no-interactive"])
    assert result.exit_code == 0
    assert "Would delete branch feature/test" in result.stdout


def test_main_interactive_mode(runner, git_env, monkeypatch):
    """Test interactive mode."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete a branch
    git_env.create_branch("feature/test", "Test feature branch")
    git_env.delete_remote_branch("feature/test")

    result = runner.invoke(app, [], input="y\n")
    assert result.exit_code == 0
    assert "feature/test" in result.stdout


def test_main_no_gc(runner, git_env, monkeypatch):
    """Test skipping garbage collection."""
    monkeypatch.chdir(git_env.repo_dir)
    result = runner.invoke(app, ["--no-gc", "--no-interactive"])
    assert result.exit_code == 0


def test_main_protect_branches(runner, git_env, monkeypatch):
    """Test protected branches are not deleted."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete a protected branch
    git_env.create_branch("develop", "Protected branch")
    git_env.delete_remote_branch("develop")

    result = runner.invoke(app, ["--protect", "develop", "--no-interactive"])
    assert result.exit_code == 0
    assert "All gone branches are protected" in result.stdout


def test_delete_branches_interactive_individual_choices(runner, git_env, monkeypatch):
    """Test interactive deletion with individual branch choices."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete two branches
    git_env.create_branch("feature/123", "Feature 123")
    git_env.create_branch("feature/456", "Feature 456")
    git_env.delete_remote_branch("feature/123")
    git_env.delete_remote_branch("feature/456")

    result = runner.invoke(app, [], input="y\ny\nn\n")
    assert result.exit_code == 0
    assert "feature/123" in result.stdout
    assert "feature/456" in result.stdout


def test_delete_remote_branches_interactive_confirm(runner, git_env, monkeypatch):
    """Test interactive deletion of remote branches with confirmation."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete two branches
    git_env.create_branch("feature/123", "Feature 123")
    git_env.create_branch("feature/456", "Feature 456")
    git_env.delete_remote_branch("feature/123")
    git_env.delete_remote_branch("feature/456")

    result = runner.invoke(app, [], input="y\ny\ny\n")
    assert result.exit_code == 0
    assert "feature/123" in result.stdout
    assert "feature/456" in result.stdout


def test_delete_remote_branches_interactive_reject(runner, git_env, monkeypatch):
    """Test rejecting remote branch deletion in interactive mode."""
    monkeypatch.chdir(git_env.repo_dir)

    # Create and delete a branch
    git_env.create_branch("feature/test", "Test feature branch")
    git_env.delete_remote_branch("feature/test")

    result = runner.invoke(app, [], input="n\n")
    assert result.exit_code == 0
    assert "feature/test" in result.stdout
