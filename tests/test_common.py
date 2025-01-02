"""Tests for common git functionality."""

from pathlib import Path

import pytest
from arborist.exceptions import GitError
from arborist.git.common import (
    get_branch,
    get_current_branch_name,
    get_latest_commit_sha,
    is_branch_upstream_of_another,
    log_git_error,
    validate_branch_doesnt_exist,
    validate_branch_exists,
    validate_branch_name,
)
from git import GitCommandError, Repo
from git.repo.base import Repo as GitRepo


@pytest.fixture
def temp_repo(tmp_path: Path) -> GitRepo:
    """Create a temporary git repository.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path

    Returns
    -------
    GitRepo
        Temporary git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path, initial_branch="main")

    # Create initial commit
    readme_path = repo_path / "README.md"
    readme_path.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return repo


def test_validate_branch_name() -> None:
    """Test branch name validation."""
    # Valid branch names
    validate_branch_name("feature/test")
    validate_branch_name("release-1.0")
    validate_branch_name("hotfix_123")
    validate_branch_name("main")

    # Invalid branch names
    with pytest.raises(GitError, match="Branch name cannot be empty"):
        validate_branch_name("")

    with pytest.raises(GitError, match="contains invalid characters"):
        validate_branch_name("feature~test")
        validate_branch_name("feature test")
        validate_branch_name("feature*test")
        validate_branch_name("feature?test")
        validate_branch_name("feature[test]")
        validate_branch_name("feature\\test")

    with pytest.raises(GitError, match="is invalid"):
        validate_branch_name("-feature")
        validate_branch_name("feature-")
        validate_branch_name("/feature")
        validate_branch_name("feature/")


def test_validate_branch_exists(temp_repo: GitRepo) -> None:
    """Test branch existence validation.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test with existing branch
    validate_branch_exists(temp_repo, "main")

    # Test with non-existent branch
    with pytest.raises(GitError, match="does not exist"):
        validate_branch_exists(temp_repo, "nonexistent")


def test_validate_branch_doesnt_exist(temp_repo: GitRepo) -> None:
    """Test branch non-existence validation.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test with non-existent branch
    validate_branch_doesnt_exist(temp_repo, "feature/test")

    # Test with existing branch
    with pytest.raises(GitError, match="already exists"):
        validate_branch_doesnt_exist(temp_repo, "main")


def test_get_branch(temp_repo: GitRepo) -> None:
    """Test getting a branch by name.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test with existing branch
    branch = get_branch(temp_repo, "main")
    assert branch.name == "main"

    # Test with non-existent branch
    with pytest.raises(GitError, match="does not exist"):
        get_branch(temp_repo, "nonexistent")


def test_get_current_branch_name(temp_repo: GitRepo) -> None:
    """Test getting current branch name.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test with normal branch
    assert get_current_branch_name(temp_repo) == "main"

    # Test with detached HEAD
    temp_repo.head.reference = temp_repo.head.commit
    with pytest.raises(GitError, match="Failed to determine current branch"):
        get_current_branch_name(temp_repo)


def test_get_latest_commit_sha(temp_repo: GitRepo) -> None:
    """Test getting latest commit SHA.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Test with existing branch
    sha = get_latest_commit_sha(temp_repo, "main")
    assert len(sha) == 40  # SHA-1 is 40 characters

    # Test with non-existent branch
    with pytest.raises(GitError, match="does not exist"):
        get_latest_commit_sha(temp_repo, "nonexistent")

    # Test with invalid branch name
    with pytest.raises(GitError, match="contains invalid characters"):
        get_latest_commit_sha(temp_repo, "invalid~branch")


def test_is_branch_upstream_of_another(temp_repo: GitRepo) -> None:
    """Test checking if one branch is upstream of another.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    # Create a feature branch and add a commit
    temp_repo.create_head("feature", "HEAD")
    temp_repo.heads.feature.checkout()
    test_file = Path(temp_repo.working_dir) / "test.txt"
    test_file.write_text("test")
    temp_repo.index.add([str(test_file)])
    temp_repo.index.commit("Feature commit")

    # main should be upstream of feature
    assert is_branch_upstream_of_another(temp_repo, "main", "feature")
    assert not is_branch_upstream_of_another(temp_repo, "feature", "main")

    # Test with non-existent branch
    with pytest.raises(GitError, match="does not exist"):
        is_branch_upstream_of_another(temp_repo, "main", "nonexistent")
        is_branch_upstream_of_another(temp_repo, "nonexistent", "main")

    # Test with invalid branch names
    with pytest.raises(GitError, match="contains invalid characters"):
        is_branch_upstream_of_another(temp_repo, "invalid~branch", "main")
        is_branch_upstream_of_another(temp_repo, "main", "invalid~branch")


def test_log_git_error(caplog: pytest.LogCaptureFixture) -> None:
    """Test git error logging.

    Parameters
    ----------
    caplog : pytest.LogCaptureFixture
        Fixture to capture log messages
    """
    # Test with GitError
    error = GitError("test error")
    log_git_error(error, "Test message")
    assert "Test message: test error" in caplog.text

    # Test with GitCommandError
    error = GitCommandError("git", 1)
    log_git_error(error, "Test message")
    assert "Test message" in caplog.text
