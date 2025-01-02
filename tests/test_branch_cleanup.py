"""Tests for branch cleanup operations."""

import logging
from pathlib import Path
from typing import Generator

import pytest
from git import Repo
from git.repo.base import Repo as GitRepo

from arborist.exceptions import GitError
from arborist.git.branch_cleanup import BranchCleanup

# Configure root logger to show debug messages
logging.basicConfig(level=logging.DEBUG)

# Configure package logger
logger = logging.getLogger("arborist")
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Add formatter to ch
ch.setFormatter(formatter)

# Add ch to logger
logger.addHandler(ch)


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
def cleanup_manager(temp_repo: GitRepo) -> BranchCleanup:
    """Create a branch cleanup manager.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository

    Returns
    -------
    BranchCleanup
        Branch cleanup manager instance
    """
    return BranchCleanup(temp_repo)


def test_is_protected_by_pattern(cleanup_manager: BranchCleanup) -> None:
    """Test branch protection pattern matching.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    """
    # Test empty patterns
    assert not cleanup_manager._is_protected_by_pattern("feature/test", [])

    # Test matching patterns
    patterns = ["main", "master", "develop"]
    assert cleanup_manager._is_protected_by_pattern("main", patterns)
    assert cleanup_manager._is_protected_by_pattern("master", patterns)
    assert cleanup_manager._is_protected_by_pattern("develop", patterns)
    assert not cleanup_manager._is_protected_by_pattern("feature/test", patterns)


def test_get_branches_to_delete(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test getting branches to delete.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create branches with different states
    # 1. Merged branch
    temp_repo.create_head("feature/merged", "HEAD")
    temp_repo.heads["feature/merged"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "merged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["merged.txt"])
    temp_repo.index.commit("Merged branch commit")
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/merged")

    # 2. Gone branch
    temp_repo.create_head("feature/gone", "HEAD")
    temp_repo.heads["feature/gone"].checkout()
    temp_repo.git.push("--set-upstream", "origin", "feature/gone")
    temp_repo.git.push("origin", "--delete", "feature/gone")

    # 3. Unmerged branch
    temp_repo.create_head("feature/unmerged", "HEAD")
    temp_repo.heads["feature/unmerged"].checkout()
    test_file = working_dir / "unmerged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["unmerged.txt"])
    temp_repo.index.commit("Unmerged branch commit")

    # 4. Protected branch
    temp_repo.create_head("develop", "HEAD")

    # Switch back to main before running tests
    temp_repo.heads.main.checkout()

    # Test without force
    to_delete = cleanup_manager._get_branches_to_delete(force=False, protect=["main", "develop"])
    assert "feature/merged" in to_delete
    assert "feature/gone" in to_delete
    assert "feature/unmerged" not in to_delete
    assert "develop" not in to_delete
    assert "main" not in to_delete

    # Test with force
    to_delete = cleanup_manager._get_branches_to_delete(force=True, protect=["main", "develop"])
    assert "feature/merged" in to_delete
    assert "feature/gone" in to_delete
    assert "feature/unmerged" in to_delete
    assert "develop" not in to_delete
    assert "main" not in to_delete


def test_validate_branch_exists(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test branch existence validation.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test existing branch
    temp_repo.create_head("feature/test", "HEAD")
    cleanup_manager._validate_branch_exists("feature/test")

    # Test non-existent branch
    with pytest.raises(GitError):
        cleanup_manager._validate_branch_exists("nonexistent")


def test_validate_not_current_branch(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test current branch validation.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and checkout a branch
    temp_repo.create_head("feature/test", "HEAD")
    temp_repo.heads["feature/test"].checkout()

    # Test current branch
    with pytest.raises(GitError):
        cleanup_manager._validate_not_current_branch("feature/test")

    # Test different branch
    cleanup_manager._validate_not_current_branch("main")


def test_validate_branch_merged(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test branch merge status validation.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and merge a branch
    temp_repo.create_head("feature/merged", "HEAD")
    temp_repo.heads["feature/merged"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "merged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["merged.txt"])
    temp_repo.index.commit("Merged branch commit")
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/merged")

    # Create an unmerged branch
    temp_repo.create_head("feature/unmerged", "HEAD")
    temp_repo.heads["feature/unmerged"].checkout()
    test_file = working_dir / "unmerged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["unmerged.txt"])
    temp_repo.index.commit("Unmerged branch commit")
    temp_repo.heads.main.checkout()

    # Test merged branch
    cleanup_manager._validate_branch_merged("feature/merged")

    # Test unmerged branch
    with pytest.raises(GitError):
        cleanup_manager._validate_branch_merged("feature/unmerged")


def test_find_safe_branch(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test finding a safe branch to switch to.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create some branches
    temp_repo.create_head("feature/test1", "HEAD")
    temp_repo.create_head("feature/test2", "HEAD")
    temp_repo.create_head("develop", "HEAD")

    # Test finding safe branch when current branch is in to_delete
    safe_branch = cleanup_manager._find_safe_branch("feature/test1", {"feature/test1", "feature/test2"})
    assert safe_branch in {"main", "develop"}

    # Test when current branch is not in to_delete
    safe_branch = cleanup_manager._find_safe_branch("develop", {"feature/test1", "feature/test2"})
    assert safe_branch is None


def test_delete_single_branch(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test deleting a single branch.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and merge a branch
    temp_repo.create_head("feature/merged", "HEAD")
    temp_repo.heads["feature/merged"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "merged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["merged.txt"])
    temp_repo.index.commit("Merged branch commit")
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/merged")

    # Create an unmerged branch
    temp_repo.create_head("feature/unmerged", "HEAD")
    temp_repo.heads["feature/unmerged"].checkout()
    test_file = working_dir / "unmerged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["unmerged.txt"])
    temp_repo.index.commit("Unmerged branch commit")
    temp_repo.heads.main.checkout()

    # Get branch status
    status = cleanup_manager.status_manager.get_branch_status()

    # Test deleting merged branch
    success, error = cleanup_manager._delete_single_branch("feature/merged", False, status)
    assert success
    assert error is None
    assert "feature/merged" not in temp_repo.heads

    # Test deleting unmerged branch without force
    success, error = cleanup_manager._delete_single_branch("feature/unmerged", False, status)
    assert not success
    assert error is not None
    assert "feature/unmerged" in temp_repo.heads

    # Test deleting unmerged branch with force
    success, error = cleanup_manager._delete_single_branch("feature/unmerged", True, status)
    assert success
    assert error is None
    assert "feature/unmerged" not in temp_repo.heads


def test_delete_branch(cleanup_manager: BranchCleanup, temp_repo: GitRepo) -> None:
    """Test the public delete_branch method.

    Parameters
    ----------
    cleanup_manager : BranchCleanup
        Branch cleanup manager instance
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create and merge a branch
    temp_repo.create_head("feature/merged", "HEAD")
    temp_repo.heads["feature/merged"].checkout()
    working_dir = Path(temp_repo.working_dir)
    test_file = working_dir / "merged.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")
    temp_repo.index.add(["merged.txt"])
    temp_repo.index.commit("Merged branch commit")
    temp_repo.heads.main.checkout()
    temp_repo.git.merge("feature/merged")

    # Test deleting merged branch
    cleanup_manager.delete_branch("feature/merged")
    assert "feature/merged" not in temp_repo.heads

    # Test deleting non-existent branch
    with pytest.raises(GitError):
        cleanup_manager.delete_branch("nonexistent")

    # Test deleting current branch
    temp_repo.create_head("feature/current", "HEAD")
    temp_repo.heads["feature/current"].checkout()
    with pytest.raises(GitError):
        cleanup_manager.delete_branch("feature/current")
