"""Test branch cleanup edge cases."""

from arborist.git.branch_cleanup import BranchCleanup
from git.repo.base import Repo


def test_no_branches_to_delete(temp_repo: Repo) -> None:
    """Test cleanup with no branches to delete."""
    cleanup = BranchCleanup(temp_repo)
    to_delete = cleanup._get_branches_to_delete(force=False)
    assert not to_delete


def test_protect_patterns(temp_repo: Repo) -> None:
    """Test branch protection patterns."""
    cleanup = BranchCleanup(temp_repo)

    # Create some branches
    temp_repo.create_head("main-1.0")
    temp_repo.create_head("feature/test")
    temp_repo.create_head("bugfix/123")

    # Test exact match
    to_delete = cleanup._get_branches_to_delete(force=False, protect=["main-1.0"])
    assert "main-1.0" not in to_delete

    # Test wildcard pattern
    to_delete = cleanup._get_branches_to_delete(force=False, protect=["feature/*"])
    assert "feature/test" not in to_delete

    # Test prefix match
    to_delete = cleanup._get_branches_to_delete(force=False, protect=["bugfix"])
    assert "bugfix/123" not in to_delete


def test_current_branch_protection(temp_repo: Repo) -> None:
    """Test current branch is always protected."""
    cleanup = BranchCleanup(temp_repo)

    # Create and checkout a new branch
    temp_repo.create_head("test").checkout()

    # Try to get branches to delete
    to_delete = cleanup._get_branches_to_delete(force=False)
    assert "test" not in to_delete


def test_remote_tracking_protection(temp_repo: Repo) -> None:
    """Test branches with remote tracking are protected unless forced."""
    cleanup = BranchCleanup(temp_repo)

    # Create a branch with remote tracking
    temp_repo.create_head("test")
    temp_repo.git.push("--set-upstream", "origin", "test")

    # Without force
    to_delete = cleanup._get_branches_to_delete(force=False)
    assert "test" not in to_delete

    # With force
    to_delete = cleanup._get_branches_to_delete(force=True)
    assert "test" in to_delete
