"""Tests for worktree operations."""

from pathlib import Path
from typing import Generator

import pytest
from arborist.errors import ErrorCode, GitError
from arborist.git.worktree import WorktreeInfo, WorktreeManager
from git import Repo
from git.repo.base import Repo as GitRepo


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

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    yield repo

    # Cleanup
    repo.close()


@pytest.fixture
def worktree_manager(temp_repo: GitRepo) -> WorktreeManager:
    """Create a worktree manager.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository

    Returns
    -------
    WorktreeManager
        Worktree manager instance
    """
    return WorktreeManager(temp_repo)


def test_parse_worktree_line() -> None:
    """Test parsing worktree list output."""
    manager = WorktreeManager(None)  # type: ignore
    line = "/path/to/worktree abcd1234 [branch feature/test]"
    info = manager._parse_worktree_line(line)

    assert isinstance(info, WorktreeInfo)
    assert info.path == Path("/path/to/worktree")
    assert info.branch == "feature/test"
    assert info.commit == "abcd1234"
    assert not info.is_bare
    assert not info.is_detached
    assert not info.is_prunable


def test_parse_worktree_line_detached() -> None:
    """Test parsing worktree list output with detached HEAD."""
    manager = WorktreeManager(None)  # type: ignore
    line = "/path/to/worktree abcd1234 (HEAD detached at abcd123)"
    info = manager._parse_worktree_line(line)

    assert isinstance(info, WorktreeInfo)
    assert info.path == Path("/path/to/worktree")
    assert info.branch is None
    assert info.commit == "abcd1234"
    assert not info.is_bare
    assert info.is_detached
    assert not info.is_prunable


def test_parse_worktree_line_bare() -> None:
    """Test parsing worktree list output with bare repository."""
    manager = WorktreeManager(None)  # type: ignore
    line = "/path/to/worktree abcd1234 [bare]"
    info = manager._parse_worktree_line(line)

    assert isinstance(info, WorktreeInfo)
    assert info.path == Path("/path/to/worktree")
    assert info.branch is None
    assert info.commit == "abcd1234"
    assert info.is_bare
    assert info.is_detached
    assert not info.is_prunable


def test_parse_worktree_line_prunable() -> None:
    """Test parsing worktree list output with prunable worktree."""
    manager = WorktreeManager(None)  # type: ignore
    line = "/path/to/worktree abcd1234 [prunable]"
    info = manager._parse_worktree_line(line)

    assert isinstance(info, WorktreeInfo)
    assert info.path == Path("/path/to/worktree")
    assert info.branch is None
    assert info.commit == "abcd1234"
    assert not info.is_bare
    assert info.is_detached
    assert info.is_prunable


def test_parse_worktree_line_invalid() -> None:
    """Test parsing invalid worktree list output."""
    manager = WorktreeManager(None)  # type: ignore
    with pytest.raises(GitError) as exc_info:
        manager._parse_worktree_line("invalid")

    assert exc_info.value.code == ErrorCode.WORKTREE_ERROR
    assert "Failed to parse worktree information" in exc_info.value.message


def test_list_worktrees(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test listing worktrees.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    # Add a worktree
    worktree_path = tmp_path / "test_worktree"
    worktree_manager.add_worktree(worktree_path, new_branch="feature/test")

    # List worktrees
    worktrees = worktree_manager.list_worktrees()
    assert len(worktrees) >= 1

    # Find our worktree
    test_worktree = next(
        (wt for wt in worktrees if wt.path == worktree_path),
        None,
    )
    assert test_worktree is not None
    assert test_worktree.branch == "feature/test"


def test_get_worktree_for_branch(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test getting worktree for branch.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    # Add a worktree
    worktree_path = tmp_path / "test_worktree"
    worktree_manager.add_worktree(worktree_path, new_branch="feature/test")

    # Get worktree for branch
    worktree = worktree_manager.get_worktree_for_branch("feature/test")
    assert worktree is not None
    assert worktree.path == worktree_path
    assert worktree.branch == "feature/test"


def test_add_worktree(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test adding a worktree.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    worktree_path = tmp_path / "test_worktree"
    worktree_manager.add_worktree(worktree_path, new_branch="feature/test")

    assert worktree_path.exists()
    assert worktree_path.is_dir()

    worktree = worktree_manager.get_worktree_for_branch("feature/test")
    assert worktree is not None
    assert worktree.path == worktree_path


def test_remove_worktree(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test removing a worktree.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    # Add a worktree
    worktree_path = tmp_path / "test_worktree"
    worktree_manager.add_worktree(worktree_path, new_branch="feature/test")

    # Remove the worktree
    worktree_manager.remove_worktree(worktree_path)

    # Check that the worktree is gone
    worktree = worktree_manager.get_worktree_for_branch("feature/test")
    assert worktree is None


def test_prune_worktrees(worktree_manager: WorktreeManager) -> None:
    """Test pruning worktrees.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    """
    # Just test that it doesn't raise an exception
    worktree_manager.prune_worktrees()


def test_move_worktree(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test moving a worktree.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    # Add a worktree
    old_path = tmp_path / "old_worktree"
    new_path = tmp_path / "new_worktree"
    worktree_manager.add_worktree(old_path, new_branch="feature/test")

    # Move the worktree
    worktree_manager.move_worktree(old_path, new_path)

    # Check that the worktree was moved
    worktree = worktree_manager.get_worktree_for_branch("feature/test")
    assert worktree is not None
    assert worktree.path == new_path


def test_lock_unlock_worktree(worktree_manager: WorktreeManager, tmp_path: Path) -> None:
    """Test locking and unlocking a worktree.

    Parameters
    ----------
    worktree_manager : WorktreeManager
        Worktree manager instance
    tmp_path : Path
        Temporary directory path
    """
    # Add a worktree
    worktree_path = tmp_path / "test_worktree"
    worktree_manager.add_worktree(worktree_path, new_branch="feature/test")

    # Lock the worktree
    worktree_manager.lock_worktree(worktree_path, "Testing")

    # Unlock the worktree
    worktree_manager.unlock_worktree(worktree_path)
