"""Test git functionality."""

import os

import pytest
from arborist import git

from tests.git_test_env import GitHubTestEnvironment


@pytest.fixture
def git_env():
    """Create a Git test environment."""
    env = GitHubTestEnvironment()
    env.setup()
    yield env
    env.cleanup()


def test_run_git_command(git_env):
    """Test running git commands."""
    os.chdir(git_env.repo_dir)  # Ensure we're in the test repo
    stdout, stderr = git.run_git_command(["status"])
    assert "On branch main" in stdout
    assert not stderr


def test_run_git_command_error(git_env, tmp_path):
    """Test handling git command errors."""
    os.chdir(tmp_path)  # Move to non-git directory
    with pytest.raises(git.GitError, match="not a git repository"):
        git.run_git_command(["status"])


def test_run_git_command_silent_error(git_env, tmp_path):
    """Test silent error handling."""
    os.chdir(tmp_path)  # Move to non-git directory
    stdout, stderr = git.run_git_command(["status"], silent=True)
    assert stdout == ""
    assert "not a git repository" in stderr


def test_is_git_repo(git_env):
    """Test git repository detection."""
    os.chdir(git_env.repo_dir)
    assert git.is_git_repo()


def test_is_not_git_repo(tmp_path):
    """Test non-git repository detection."""
    os.chdir(tmp_path)
    assert not git.is_git_repo()


def test_get_gone_branches(git_env):
    """Test detecting branches with gone remotes."""
    os.chdir(git_env.repo_dir)

    # Create and push a feature branch
    git_env.create_branch("feature/123", "Feature 123")
    git_env.push_branch("feature/123")

    # Delete the remote branch
    git_env.delete_remote_branch("feature/123")

    # Check for gone branches
    branches = git.get_gone_branches()
    assert branches == ["feature/123"]


def test_get_merged_branches(git_env):
    """Test detecting merged branches."""
    os.chdir(git_env.repo_dir)

    # Create and merge feature branches
    git_env.create_branch("feature/456", "Feature 456")
    git_env.create_branch("hotfix/789", "Hotfix 789")
    git_env.merge_branch("feature/456")
    git_env.merge_branch("hotfix/789")

    branches = git.get_merged_branches()
    assert set(branches) == {"feature/456", "hotfix/789"}


def test_delete_branch(git_env):
    """Test branch deletion."""
    os.chdir(git_env.repo_dir)

    # Create a branch
    git_env.create_branch("feature/123", "Feature 123")

    # Delete it
    git.delete_branch("feature/123")

    # Verify it's gone
    assert "feature/123" not in git_env.get_branches()


def test_delete_branch_force(git_env):
    """Test forced branch deletion."""
    os.chdir(git_env.repo_dir)

    # Create a branch with unmerged changes
    git_env.create_branch("feature/123", "Feature 123")
    git_env.commit_file("test.txt", "test content", branch="feature/123")

    # Delete it with force
    git.delete_branch("feature/123", force=True)

    # Verify it's gone
    assert "feature/123" not in git_env.get_branches()


def test_delete_branch_with_special_chars(git_env):
    """Test branch deletion with special characters."""
    os.chdir(git_env.repo_dir)

    # Create a branch with special characters
    git_env.create_branch("feature-123#test", "Feature with special chars")

    # Delete it
    git.delete_branch("feature-123#test")

    # Verify it's gone
    assert "feature-123#test" not in git_env.get_branches()


def test_optimize_repo(git_env):
    """Test repository optimization."""
    os.chdir(git_env.repo_dir)

    # Create and delete some branches to generate garbage
    git_env.create_branch("feature/1", "Feature 1")
    git_env.create_branch("feature/2", "Feature 2")
    git_env.delete_remote_branch("feature/1")
    git_env.delete_remote_branch("feature/2")

    # Run optimization
    git.optimize_repo()


def test_fetch_and_prune(git_env):
    """Test fetch and prune operation."""
    os.chdir(git_env.repo_dir)

    # Create and delete a remote branch
    git_env.create_branch("feature/test", "Feature test")
    git_env.push_branch("feature/test")
    git_env.delete_remote_branch("feature/test")

    # Fetch and prune
    git.fetch_and_prune()


def test_filter_protected_branches():
    """Test filtering protected branches."""
    branches = ["main", "develop", "feature/123"]
    protected = ["main"]
    filtered = git.filter_protected_branches(branches, protected)
    assert filtered == ["develop", "feature/123"]


def test_get_merged_remote_branches(git_env):
    """Test getting merged remote branches."""
    os.chdir(git_env.repo_dir)

    # Create and push feature branches
    git_env.create_branch("feature/1", "Feature 1")
    git_env.create_branch("feature/2", "Feature 2")
    git_env.push_branch("feature/1")
    git_env.push_branch("feature/2")

    # Merge one branch
    git_env.merge_branch("feature/1")

    # Get merged remote branches
    branches = git.get_merged_remote_branches()
    assert "feature/1" in branches
    assert "feature/2" not in branches


def test_get_merged_remote_branches_empty(git_env):
    """Test getting merged remote branches when none exist."""
    os.chdir(git_env.repo_dir)
    branches = git.get_merged_remote_branches()
    assert not branches


def test_get_merged_remote_branches_with_current(git_env):
    """Test getting merged remote branches with current branch remote."""
    os.chdir(git_env.repo_dir)

    # Create and push feature branches
    git_env.create_branch("feature/1", "Feature 1")
    git_env.create_branch("feature/2", "Feature 2")
    git_env.push_branch("feature/1")
    git_env.push_branch("feature/2")

    # Switch to feature/1 and merge feature/2
    git_env.switch_branch("feature/1")
    git_env.merge_branch("feature/2", "feature/1")

    # Get merged remote branches
    branches = git.get_merged_remote_branches()
    assert "feature/2" in branches
    assert "feature/1" not in branches  # Current branch should be excluded


def test_delete_remote_branch(git_env):
    """Test deleting a remote branch."""
    os.chdir(git_env.repo_dir)

    # Create and push a feature branch
    git_env.create_branch("feature/1", "Feature 1")
    git_env.push_branch("feature/1")

    # Delete it
    git.delete_remote_branch("feature/1")

    # Verify it's gone
    assert "feature/1" not in git_env.get_remote_branches()


def test_delete_remote_branch_error(git_env):
    """Test error handling when deleting a remote branch."""
    os.chdir(git_env.repo_dir)

    # Create a branch that doesn't exist remotely
    branch_name = "non-existent-branch"
    git.create_branch(branch_name)

    with pytest.raises(git.GitError):
        git.delete_remote_branch(branch_name)
