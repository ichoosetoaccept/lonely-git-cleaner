"""Tests for branch operations."""

import logging
from pathlib import Path
from typing import Generator

import pytest
from git import Repo
from git.repo.base import Repo as GitRepo

from arborist.errors import GitError
from arborist.git.branch_operations import BranchOperations

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

    # Test non-current branch (should not raise)
    branch_ops._validate_not_current_branch(temp_repo.heads["main"])

    # Test current branch (should raise)
    with pytest.raises(GitError):
        branch_ops._validate_not_current_branch(temp_repo.active_branch)


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

    # Test unprotected branch (should not raise)
    branch_ops._validate_not_protected(temp_repo.heads["feature/test"], ["main", "develop"])

    # Test protected branch (should raise)
    with pytest.raises(GitError):
        branch_ops._validate_not_protected(temp_repo.heads["develop"], ["main", "develop"])


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

    # Test deleting unprotected branch (should succeed)
    branch_ops.delete_branch("feature/test")
    assert "feature/test" not in temp_repo.heads

    # Test deleting protected branch (should raise)
    with pytest.raises(GitError):
        branch_ops.delete_branch("develop", protected_branches=["main", "develop"])

    # Test deleting current branch (should raise)
    temp_repo.heads["develop"].checkout()
    with pytest.raises(GitError):
        branch_ops.delete_branch("develop")
