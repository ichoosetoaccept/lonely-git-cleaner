"""Tests for branch operations."""

import logging
from pathlib import Path
from typing import Generator

import pytest
from arborist.exceptions import GitError
from arborist.git.branch_operations import BranchOperations
from git import Repo
from git.repo.base import Repo as GitRepo

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def temp_repo(tmp_path: Path) -> Generator[GitRepo, None, None]:
    """Create a temporary git repository.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path

    Yields
    ------
    GitRepo
        Temporary git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path, initial_branch="main")

    # Create initial commit on main
    readme_path = repo_path / "README.md"
    readme_path.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    # Create a remote
    remote_path = tmp_path / "remote"
    remote_path.mkdir()
    remote = Repo.init(remote_path, bare=True)
    repo.create_remote("origin", str(remote_path))
    repo.git.push("origin", "HEAD:main")

    yield repo

    # Cleanup
    repo.close()
    remote.close()


@pytest.fixture
def branch_ops(temp_repo: GitRepo) -> BranchOperations:
    """Create a branch operations manager.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository

    Returns
    -------
    BranchOperations
        Branch operations manager instance
    """
    return BranchOperations(temp_repo)


def test_validate_not_current_branch(branch_ops: BranchOperations, temp_repo: GitRepo) -> None:
    """Test validation of current branch.

    Parameters
    ----------
    branch_ops : BranchOperations
        Branch operations manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and checkout a branch
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.heads["feature/test"].checkout()

    # Test current branch
    with pytest.raises(GitError, match="Cannot delete current branch 'feature/test'"):
        branch_ops._validate_not_current_branch(temp_repo.active_branch)

    # Test different branch
    temp_repo.heads.main.checkout()
    branch_ops._validate_not_current_branch(temp_repo.heads["feature/test"])


def test_validate_not_protected(branch_ops: BranchOperations, temp_repo: GitRepo) -> None:
    """Test validation of protected branches.

    Parameters
    ----------
    branch_ops : BranchOperations
        Branch operations manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create test branches
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.create_head("develop", "HEAD")

    # Test protected branch
    protected_branches = ["main", "develop"]
    with pytest.raises(GitError, match="Cannot delete protected branch 'develop'"):
        branch_ops._validate_not_protected(temp_repo.heads["develop"], protected_branches)

    # Test unprotected branch
    branch_ops._validate_not_protected(temp_repo.heads["feature/test"], protected_branches)


def test_handle_worktree_deletion(branch_ops: BranchOperations, temp_repo: GitRepo) -> None:
    """Test handling of worktree deletion.

    Parameters
    ----------
    branch_ops : BranchOperations
        Branch operations manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create a branch and add a worktree
    temp_repo.create_head("feature/test", "HEAD")
    worktree_path = Path(temp_repo.working_dir).parent / "worktree"
    temp_repo.git.worktree("add", str(worktree_path), "feature/test")

    # Test worktree deletion
    branch_ops._handle_worktree_deletion(temp_repo.heads["feature/test"])
    assert not worktree_path.exists()


def test_delete_branch_safely(branch_ops: BranchOperations, temp_repo: GitRepo) -> None:
    """Test safe branch deletion.

    Parameters
    ----------
    branch_ops : BranchOperations
        Branch operations manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and push a branch
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.git.push("origin", "feature/test")
    temp_repo.heads["feature/test"].set_tracking_branch(temp_repo.remotes.origin.refs["feature/test"])

    # Test branch deletion
    branch_ops._delete_branch_safely(temp_repo.heads["feature/test"])
    assert "feature/test" not in temp_repo.heads
    assert "feature/test" not in temp_repo.remotes.origin.refs


def test_delete_branch(branch_ops: BranchOperations, temp_repo: GitRepo) -> None:
    """Test branch deletion.

    Parameters
    ----------
    branch_ops : BranchOperations
        Branch operations manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create test branches
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.create_head("develop", "HEAD")

    # Test deleting protected branch
    with pytest.raises(GitError, match="Cannot delete protected branch 'develop'"):
        branch_ops.delete_branch("develop", protected_branches=["main", "develop"])

    # Test deleting current branch
    temp_repo.heads["feature/test"].checkout()
    with pytest.raises(GitError, match="Cannot delete current branch 'feature/test'"):
        branch_ops.delete_branch("feature/test")

    # Test successful deletion
    temp_repo.heads.main.checkout()
    branch_ops.delete_branch("feature/test")
    assert "feature/test" not in temp_repo.heads
