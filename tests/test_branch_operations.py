"""Tests for branch operations."""

import logging
import os
from pathlib import Path
from typing import Generator

import pytest
from git import Repo
from git.repo.base import Repo as GitRepo

from arborist.errors import ErrorCode, GitError
from arborist.git.branch_operations import BranchOperations

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


def test_delete_branch_safely_with_errors(test_repo: GitRepo) -> None:
    """Test error handling in safe branch deletion.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branches
    test_repo.create_head("feature/test")
    test_repo.create_head("feature/changes")

    # Create changes in feature/changes branch
    test_repo.heads["feature/changes"].checkout()
    changes_file = Path(test_repo.working_dir) / "changes.txt"
    changes_file.write_text("Uncommitted changes")
    test_repo.index.add([str(changes_file)])
    test_repo.index.commit("Add changes")

    # Create another change but don't commit it
    changes_file.write_text("More uncommitted changes")
    test_repo.index.add([str(changes_file)])

    # Should raise when trying to delete branch with changes
    with pytest.raises(GitError, match="Cannot delete current branch 'feature/changes'"):
        branch_ops._delete_branch_safely(test_repo.heads["feature/changes"])

    # Switch back to main
    test_repo.git.stash("save")
    test_repo.heads["main"].checkout()

    # Should raise when trying to delete unmerged branch
    with pytest.raises(GitError, match="Failed to delete branch"):
        branch_ops._delete_branch_safely(test_repo.heads["feature/changes"])

    # Create and push test branch
    test_repo.create_head("feature/remote")
    test_repo.git.push("--set-upstream", "origin", "feature/remote")

    # Should raise when trying to delete branch with remote tracking
    with pytest.raises(GitError, match="Cannot delete branch 'feature/remote' with remote tracking"):
        branch_ops._delete_branch_safely(test_repo.heads["feature/remote"])

    # Should delete unprotected branch
    branch_ops._delete_branch_safely(test_repo.heads["feature/test"])
    assert "feature/test" not in test_repo.heads


def test_is_branch_merged(test_repo: GitRepo) -> None:
    """Test branch merge status checking.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create and merge a branch
    merged_branch = test_repo.create_head("feature/merged")
    merged_branch.checkout()
    test_file = Path(test_repo.working_dir) / "merged.txt"
    test_file.write_text("merged branch content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on merged branch")
    test_repo.heads["main"].checkout()
    test_repo.git.merge("feature/merged")

    # Create an unmerged branch
    unmerged_branch = test_repo.create_head("feature/unmerged")
    unmerged_branch.checkout()
    test_file = Path(test_repo.working_dir) / "unmerged.txt"
    test_file.write_text("unmerged branch content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on unmerged branch")
    test_repo.heads["main"].checkout()

    # Test merged branch
    assert branch_ops._is_branch_merged(merged_branch) is True

    # Test unmerged branch
    assert branch_ops._is_branch_merged(unmerged_branch) is False


def test_get_merged_branches_with_remote(test_repo: GitRepo) -> None:
    """Test getting merged branches with remote parameter.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create and merge a branch
    merged_branch = test_repo.create_head("feature/merged")
    merged_branch.checkout()
    test_file = Path(test_repo.working_dir) / "merged.txt"
    test_file.write_text("merged branch content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on merged branch")
    test_repo.heads["main"].checkout()
    test_repo.git.merge("feature/merged")

    # Get remote
    remote = test_repo.remote()

    # Test with remote parameter
    merged_branches = branch_ops.get_merged_branches(remote=remote)
    assert "feature/merged" in merged_branches
    assert "main" not in merged_branches


def test_branch_protection_patterns(test_repo: GitRepo) -> None:
    """Test branch protection patterns.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create test branches
    test_repo.create_head("release/1.0")
    test_repo.create_head("release-candidate")
    test_repo.create_head("feature/test")

    # Test wildcard pattern
    with pytest.raises(GitError, match="Cannot delete protected branch 'release/1.0'"):
        branch_ops.delete_branch("release/1.0", protected_branches=["release/*"])

    # Test prefix pattern
    with pytest.raises(GitError, match="Cannot delete protected branch 'release-candidate'"):
        branch_ops.delete_branch("release-candidate", protected_branches=["release"])

    # Test non-matching pattern
    branch_ops.delete_branch("feature/test", protected_branches=["release/*", "main"])


def test_delete_branch_rejects_double_slashes(test_repo: GitRepo) -> None:
    """Test that branch deletion rejects names with double slashes.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)
    invalid_name = "invalid//branch"

    with pytest.raises(GitError) as excinfo:
        branch_ops.delete_branch(invalid_name)

    error = excinfo.value
    assert error.code == ErrorCode.BRANCH_ERROR, "Should use BRANCH_ERROR code"
    assert f"Branch name '{invalid_name}' contains double slashes" == str(error), "Error message should be descriptive"
    assert "consecutive forward slashes" in error.details, "Details should explain the issue"


def test_delete_branch_rejects_special_characters(test_repo: GitRepo) -> None:
    """Test that branch deletion rejects names with special characters.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)
    invalid_name = "invalid branch"

    with pytest.raises(GitError) as excinfo:
        branch_ops.delete_branch(invalid_name)

    error = excinfo.value
    assert error.code == ErrorCode.BRANCH_ERROR, "Should use BRANCH_ERROR code"
    assert f"Branch name '{invalid_name}' contains invalid characters" == str(
        error
    ), "Error message should be descriptive"
    assert "' '" in error.details, "Details should list the invalid character"


def test_delete_branch_rejects_control_characters(test_repo: GitRepo) -> None:
    """Test that branch deletion rejects names with control characters.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)
    invalid_name = "invalid\nbranch"

    with pytest.raises(GitError) as excinfo:
        branch_ops.delete_branch(invalid_name)

    error = excinfo.value
    assert error.code == ErrorCode.BRANCH_ERROR, "Should use BRANCH_ERROR code"
    assert f"Branch name '{invalid_name}' contains control characters" == str(
        error
    ), "Error message should be descriptive"
    assert "control characters" in error.details, "Details should explain the issue"
    assert invalid_name not in test_repo.heads, "Branch with control characters should not exist"


def test_delete_branch_requires_force_for_unmerged(test_repo: GitRepo) -> None:
    """Test that unmerged branches require force flag for deletion.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create an unmerged branch
    unmerged = test_repo.create_head("feature/unmerged")
    unmerged.checkout()
    test_file = Path(test_repo.working_dir) / "unmerged.txt"
    test_file.write_text("unmerged content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on unmerged branch")
    test_repo.heads["main"].checkout()

    with pytest.raises(GitError) as excinfo:
        branch_ops.delete_branch("feature/unmerged")

    error = excinfo.value
    assert isinstance(error, GitError), "Should raise GitError for unmerged branch deletion"
    assert (
        str(error) == "Branch 'feature/unmerged' is not fully merged"
    ), "Error message should indicate unmerged branch"
    assert "feature/unmerged" in test_repo.heads, "Unmerged branch should still exist"


def test_clean_with_various_options(test_repo: GitRepo) -> None:
    """Test clean method with various options.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    branch_ops = BranchOperations(test_repo)

    # Create and merge a branch
    merged = test_repo.create_head("feature/merged")
    merged.checkout()
    test_file = Path(test_repo.working_dir) / "merged.txt"
    test_file.write_text("merged content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on merged branch")
    test_repo.heads["main"].checkout()
    test_repo.git.merge("feature/merged")

    # Create a branch with gone remote
    gone = test_repo.create_head("feature/gone")
    gone.checkout()
    test_file = Path(test_repo.working_dir) / "gone.txt"
    test_file.write_text("gone content")
    test_repo.index.add([str(test_file)])
    test_repo.index.commit("Commit on gone branch")
    # Push to remote and then delete remote branch to make it "gone"
    test_repo.git.push("--set-upstream", "origin", "feature/gone")
    test_repo.git.push("origin", "--delete", "feature/gone")
    test_repo.heads["main"].checkout()

    # Test clean with dry run
    branch_ops.clean(dry_run=True)
    assert "feature/merged" in [b.name for b in test_repo.heads]
    assert "feature/gone" in [b.name for b in test_repo.heads]

    # Test clean with protection
    branch_ops.clean(protect={"feature/*"}, no_interactive=True)
    assert "feature/merged" in [b.name for b in test_repo.heads]
    assert "feature/gone" in [b.name for b in test_repo.heads]

    # Test clean with force and no verification
    branch_ops.clean(force=True, no_verify=True, no_interactive=True)
    assert "feature/merged" not in [b.name for b in test_repo.heads]
    assert "feature/gone" not in [b.name for b in test_repo.heads]
