"""Test CLI functionality."""

from collections.abc import Generator
from pathlib import Path

import pytest
from git import Repo
from typer.testing import CliRunner

from arborist.cli import app
from tests.git_test_env import GitTestEnv


def _debug_repo_state(name: str, repo: Repo) -> None:
    """Print debug information about the repository state.

    Parameters
    ----------
    name : str
        Name of the test/context being debugged
    repo : Repo
        GitPython repository object

    """
    print(f"\nDebug info for {name}:")
    print(f"Current branch: {repo.active_branch.name}")
    print("Local branches:")
    for branch in repo.heads:
        print(f"  - {branch.name}")
    print("Remote branches:")
    for ref in repo.remote().refs:
        print(f"  - {ref.name}")


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture(scope="function")
def git_test_env(tmp_path: Path) -> Generator[GitTestEnv, None, None]:
    """Create a test git environment."""
    env = GitTestEnv(tmp_path)
    yield env
    env.cleanup()


def test_status_command(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the status command."""
    # Create some branches with different states
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.push_branch("feature")
    git_test_env.merge_branch("feature", "main")

    git_test_env.create_branch("gone")
    git_test_env.create_commit()
    git_test_env.push_branch("gone")
    git_test_env.delete_remote_branch("gone")

    git_test_env.create_branch("unmerged")
    git_test_env.create_commit()

    # Run status command
    result = cli_runner.invoke(app, ["status", "--path", git_test_env.clone_dir])
    assert result.exit_code == 0
    assert "feature" in result.stdout
    assert "merged" in result.stdout.lower()
    assert "gone" in result.stdout
    assert "unmerged" in result.stdout


def test_status_command_invalid_repo(tmp_path: Path, cli_runner: CliRunner) -> None:
    """Test the status command with an invalid repository."""
    result = cli_runner.invoke(app, ["status", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "Error" in result.stdout
    assert "Not a git repository" in result.stdout


def test_delete_branch_command(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the delete-branch command."""
    # Create a branch to delete
    git_test_env.create_branch("to-delete")
    git_test_env.create_commit()
    git_test_env.checkout_branch("main")

    # Delete the branch
    result = cli_runner.invoke(
        app, ["delete-branch", "to-delete", "--path", git_test_env.clone_dir]
    )
    assert result.exit_code == 1  # Should fail without force
    assert "not fully merged" in result.stdout.lower()

    # Delete with force
    result = cli_runner.invoke(
        app, ["delete-branch", "to-delete", "--force", "--path", git_test_env.clone_dir]
    )
    assert result.exit_code == 0
    assert "Deleted branch" in result.stdout


def test_delete_branch_command_invalid_name(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the delete-branch command with invalid branch names."""
    invalid_names = [
        "",  # Empty name
        "invalid/branch",  # Contains slash but not feature/
        ".branch",  # Starts with dot
        "branch/",  # Ends with slash
        "branch..name",  # Contains double dot
        "branch name",  # Contains space
        "branch~1",  # Contains tilde
        "branch^",  # Contains caret
        "branch:name",  # Contains colon
    ]

    for name in invalid_names:
        result = cli_runner.invoke(
            app, ["delete-branch", name, "--path", git_test_env.clone_dir]
        )
        assert result.exit_code == 1
        assert "Error" in result.stdout


def test_delete_branch_command_nonexistent(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the delete-branch command with a nonexistent branch."""
    result = cli_runner.invoke(
        app, ["delete-branch", "nonexistent", "--path", git_test_env.clone_dir]
    )
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_delete_branch_command_current(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the delete-branch command on the current branch."""
    result = cli_runner.invoke(
        app, ["delete-branch", "main", "--path", git_test_env.clone_dir]
    )
    assert result.exit_code == 1
    assert "Cannot delete" in result.stdout


def test_clean_command(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the clean command."""
    # Create some branches to clean
    git_test_env.create_branch("merged")
    git_test_env.create_commit()
    git_test_env.merge_branch("merged", "main")

    git_test_env.create_branch("gone")
    git_test_env.create_commit()
    git_test_env.push_branch("gone")
    git_test_env.delete_remote_branch("gone")

    git_test_env.create_branch("protected")
    git_test_env.create_commit()
    git_test_env.merge_branch("protected", "main")

    git_test_env.checkout_branch("main")

    # Run clean command with protection
    result = cli_runner.invoke(
        app,
        [
            "clean",
            "--protect",
            "protected",
            "--no-interactive",
            "--path",
            git_test_env.clone_dir,
        ],
    )
    assert result.exit_code == 0
    assert "merged" not in git_test_env.repo.repo.heads
    assert "gone" not in git_test_env.repo.repo.heads
    assert "protected" in git_test_env.repo.repo.heads


def test_clean_command_dry_run(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the clean command in dry-run mode."""
    # Create a branch to clean
    git_test_env.create_branch("merged")
    git_test_env.create_commit()
    git_test_env.merge_branch("merged", "main")
    git_test_env.checkout_branch("main")

    # Run clean command in dry-run mode
    result = cli_runner.invoke(
        app,
        ["clean", "--dry-run", "--no-interactive", "--path", git_test_env.clone_dir],
    )
    assert result.exit_code == 0
    assert "would delete" in result.stdout.lower()
    assert "merged" in git_test_env.repo.repo.heads  # Branch should still exist


def test_clean_command_force(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the clean command with force option."""
    # Create an unmerged branch
    git_test_env.create_branch("unmerged")
    git_test_env.create_commit()
    git_test_env.checkout_branch("main")

    # Try to clean without force
    result = cli_runner.invoke(
        app,
        ["clean", "--no-interactive", "--path", git_test_env.clone_dir],
    )
    assert result.exit_code == 0
    assert "unmerged" in git_test_env.repo.repo.heads

    # Clean with force
    result = cli_runner.invoke(
        app,
        ["clean", "--force", "--no-interactive", "--path", git_test_env.clone_dir],
    )
    assert result.exit_code == 0
    assert "unmerged" not in git_test_env.repo.repo.heads


def test_create_branch_command(git_test_env: GitTestEnv, cli_runner: CliRunner) -> None:
    """Test the create-branch command."""
    # Create a new branch
    result = cli_runner.invoke(
        app,
        ["create-branch", "feature/test", "--path", git_test_env.clone_dir],
    )
    assert result.exit_code == 0
    assert "Created branch" in result.stdout
    assert "feature/test" in git_test_env.repo.repo.heads


def test_create_branch_command_invalid_name(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the create-branch command with invalid branch names."""
    invalid_names = [
        "",  # Empty name
        "invalid/branch",  # Contains slash but not feature/
        ".branch",  # Starts with dot
        "branch/",  # Ends with slash
        "branch..name",  # Contains double dot
        "branch name",  # Contains space
        "branch~1",  # Contains tilde
        "branch^",  # Contains caret
        "branch:name",  # Contains colon
    ]

    for name in invalid_names:
        result = cli_runner.invoke(
            app, ["create-branch", name, "--path", git_test_env.clone_dir]
        )
        assert result.exit_code == 1
        assert "Error" in result.stdout


def test_create_branch_command_existing(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the create-branch command with an existing branch name."""
    # Create a branch
    git_test_env.create_branch("feature/test")

    # Try to create it again
    result = cli_runner.invoke(
        app,
        ["create-branch", "feature/test", "--path", git_test_env.clone_dir],
    )
    assert result.exit_code == 1
    assert "already exists" in result.stdout


def test_create_branch_command_with_start_point(
    git_test_env: GitTestEnv, cli_runner: CliRunner
) -> None:
    """Test the create-branch command with a start point."""
    # Create a commit and get its SHA
    git_test_env.create_commit()
    start_point = git_test_env.repo.repo.head.commit.hexsha

    # Create a new branch from that commit
    result = cli_runner.invoke(
        app,
        [
            "create-branch",
            "feature/test",
            "--start-point",
            start_point,
            "--path",
            git_test_env.clone_dir,
        ],
    )
    assert result.exit_code == 0
    assert "Created branch" in result.stdout
    assert "feature/test" in git_test_env.repo.repo.heads
    assert git_test_env.repo.repo.heads["feature/test"].commit.hexsha == start_point
