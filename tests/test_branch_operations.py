"""Tests for branch operations."""

import logging
import os
from pathlib import Path
from typing import Generator

import pytest
from arborist.errors import GitError
from arborist.git.branch_operations import BranchOperations
from git import Repo
from git.repo.base import Repo as GitRepo

logger = logging.getLogger(__name__)


@pytest.fixture
def test_repo(tmp_path: Path) -> Generator[GitRepo, None, None]:
    """Create a test repository.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path

    Yields
    ------
    GitRepo
        Test repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)

    # Create initial commit on main
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository")
    repo.index.add([str(readme)])
    repo.index.commit("Initial commit")

    # Create and configure a "remote" repository
    remote_path = tmp_path / "remote"
    remote_path.mkdir()
    Repo.init(remote_path, bare=True)
    repo.create_remote("origin", str(remote_path))
    repo.git.push("origin", "main")

    # Ensure main branch is checked out
    repo.heads["main"].checkout()

    # Change working directory to repo
    old_cwd = os.getcwd()
    os.chdir(repo_path)

    yield repo

    # Restore working directory
    os.chdir(old_cwd)


def test_validate_not_current_branch(test_repo: GitRepo) -> None:
    """Test validation of non-current branch.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create a test branch
    test_repo.create_head("feature/test")

    # Should not raise for non-current branch
    branch_ops._validate_not_current_branch(test_repo.heads["feature/test"])

    # Should raise for current branch
    with pytest.raises(GitError, match="Cannot delete current branch 'main'"):
        branch_ops._validate_not_current_branch(test_repo.heads["main"])


def test_validate_not_protected(test_repo: GitRepo) -> None:
    """Test validation of non-protected branch.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branches
    test_repo.create_head("feature/test")
    test_repo.create_head("release/1.0")
    test_repo.create_head("release/1.0-hotfix")
    test_repo.create_head("main-1.0")

    # Should not raise for unprotected branch
    branch_ops._validate_not_protected(test_repo.heads["feature/test"], ["release/*", "main"])

    # Should raise for exact match
    with pytest.raises(GitError, match="Cannot delete protected branch 'main'"):
        branch_ops._validate_not_protected(test_repo.heads["main"], ["main"])

    # Should raise for pattern match
    with pytest.raises(GitError, match="Cannot delete protected branch 'release/1.0'"):
        branch_ops._validate_not_protected(test_repo.heads["release/1.0"], ["release/*"])

    # Should raise for prefix match
    with pytest.raises(GitError, match="Cannot delete protected branch 'main-1.0'"):
        branch_ops._validate_not_protected(test_repo.heads["main-1.0"], ["main"])


def test_delete_branch_safely(test_repo: GitRepo) -> None:
    """Test safe branch deletion.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branches
    test_repo.create_head("feature/test")
    test_repo.create_head("release/1.0")

    # Should delete unprotected branch
    branch_ops._delete_branch_safely(test_repo.heads["feature/test"])
    assert "feature/test" not in test_repo.heads

    # Should not delete current branch
    with pytest.raises(GitError, match="Cannot delete current branch 'main'"):
        branch_ops._delete_branch_safely(test_repo.heads["main"])
    assert "main" in test_repo.heads


def test_delete_branch(test_repo: GitRepo) -> None:
    """Test branch deletion.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branches
    test_repo.create_head("feature/test")
    test_repo.create_head("release/1.0")

    # Should delete unprotected branch
    branch_ops.delete_branch("feature/test")
    assert "feature/test" not in test_repo.heads

    # Should not delete protected branch
    with pytest.raises(GitError, match="Cannot delete protected branch 'release/1.0'"):
        branch_ops.delete_branch("release/1.0", protected_branches=["release/*"])
    assert "release/1.0" in test_repo.heads

    # Should not delete current branch
    with pytest.raises(GitError, match="Cannot delete current branch 'main'"):
        branch_ops.delete_branch("main")
    assert "main" in test_repo.heads


def test_branch_operations_with_remote(test_repo: GitRepo) -> None:
    """Test branch operations with remote tracking.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create and push test branch
    test_repo.create_head("feature/remote")
    test_repo.git.push("--set-upstream", "origin", "feature/remote")

    # Should delete branch with remote tracking when forced
    branch_ops.delete_branch("feature/remote", force=True)
    assert "feature/remote" not in test_repo.heads


def test_branch_operations_with_changes(test_repo: GitRepo) -> None:
    """Test branch operations with uncommitted changes.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branch with uncommitted changes
    test_repo.create_head("feature/changes")
    test_repo.heads["feature/changes"].checkout()

    # Create an uncommitted change
    changes_file = Path(test_repo.working_dir) / "changes.txt"
    changes_file.write_text("Uncommitted changes")
    test_repo.index.add([str(changes_file)])

    # Switch back to main
    test_repo.heads["main"].checkout()

    # Should delete branch with uncommitted changes when forced
    branch_ops.delete_branch("feature/changes", force=True)
    assert "feature/changes" not in test_repo.heads
