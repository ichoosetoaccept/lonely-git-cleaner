"""Tests for branch status operations."""

from pathlib import Path
from typing import Generator

import pytest
from git import Repo
from git.repo.base import Repo as GitRepo

from arborist.exceptions import GitError
from arborist.git.branch_status import BranchStatusManager
from arborist.git.common import BranchStatus


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
    repo = Repo.init(repo_path)

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
def branch_manager(temp_repo: GitRepo) -> BranchStatusManager:
    """Create a branch status manager.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository

    Returns
    -------
    BranchStatusManager
        Branch status manager instance
    """
    return BranchStatusManager(temp_repo)


def test_get_branch_status_unmerged(
    branch_manager: BranchStatusManager, temp_repo: GitRepo
) -> None:
    """Test getting status of an unmerged branch.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create a new branch with changes
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.heads["feature/test"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["test.txt"])
    temp_repo.index.commit("Test commit")

    # Check status
    status = branch_manager.get_branch_status()
    assert status["feature/test"] == BranchStatus.UNMERGED


def test_get_branch_status_merged(
    branch_manager: BranchStatusManager, temp_repo: GitRepo
) -> None:
    """Test getting status of a merged branch.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and merge a branch
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.heads["feature/test"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["test.txt"])
    temp_repo.index.commit("Test commit")

    # Merge into main
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/test")

    # Check status
    status = branch_manager.get_branch_status()
    assert status["feature/test"] == BranchStatus.MERGED


def test_get_branch_status_gone(
    branch_manager: BranchStatusManager, temp_repo: GitRepo
) -> None:
    """Test getting status of a gone branch.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create a branch and set up tracking
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.heads["feature/test"].checkout()
    temp_repo.git.push("--set-upstream", "origin", "feature/test")

    # Delete the branch on remote
    temp_repo.git.push("origin", "--delete", "feature/test")

    # Check status
    status = branch_manager.get_branch_status()
    assert status["feature/test"] == BranchStatus.GONE


def test_get_branch_status_invalid_target(branch_manager: BranchStatusManager) -> None:
    """Test getting status with invalid target branch.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    """
    with pytest.raises(GitError):
        branch_manager.get_branch_status("nonexistent")


def test_get_gone_branches(
    branch_manager: BranchStatusManager, temp_repo: GitRepo
) -> None:
    """Test getting gone branches.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create two branches and set up tracking
    temp_repo.create_head("feature/test1", "HEAD")
    temp_repo.create_head("feature/test2", "HEAD")

    temp_repo.heads["feature/test1"].checkout()
    temp_repo.git.push("--set-upstream", "origin", "feature/test1")
    temp_repo.heads["feature/test2"].checkout()
    temp_repo.git.push("--set-upstream", "origin", "feature/test2")

    # Delete one branch on remote
    temp_repo.git.push("origin", "--delete", "feature/test1")

    # Check gone branches
    gone_branches = branch_manager.get_gone_branches()
    assert "feature/test1" in gone_branches
    assert "feature/test2" not in gone_branches


def test_get_merged_branches(
    branch_manager: BranchStatusManager, temp_repo: GitRepo
) -> None:
    """Test getting merged branches.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create two branches
    temp_repo.create_head("feature/test1", "HEAD")
    temp_repo.create_head("feature/test2", "HEAD")

    # Make changes in both branches
    working_dir = Path(temp_repo.working_dir)
    for branch in ["feature/test1", "feature/test2"]:
        temp_repo.heads[branch].checkout()
        test_file = working_dir / f"{branch}.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test")
        temp_repo.index.add([f"{branch}.txt"])
        temp_repo.index.commit(f"Test commit in {branch}")

    # Merge only one branch
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/test1")

    # Check merged branches
    merged_branches = branch_manager.get_merged_branches()
    assert "feature/test1" in merged_branches
    assert "feature/test2" not in merged_branches


def test_get_merged_branches_invalid_target(
    branch_manager: BranchStatusManager,
) -> None:
    """Test getting merged branches with invalid target.

    Parameters
    ----------
    branch_manager : BranchStatusManager
        Branch status manager instance
    """
    with pytest.raises(GitError):
        branch_manager.get_merged_branches("nonexistent")
