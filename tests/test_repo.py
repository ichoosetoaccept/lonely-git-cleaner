"""Tests for GitRepo class."""

import logging
from pathlib import Path

import pytest
from arborist.exceptions import GitError
from arborist.git.repo import GitRepo as ArboristRepo
from git import Repo
from git.repo.base import Repo as GitRepo

# Configure logging
logger = logging.getLogger(__name__)


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


def test_init_with_valid_path(temp_repo: GitRepo) -> None:
    """Test initializing GitRepo with a valid path.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    assert repo.repo.working_dir == temp_repo.working_dir


def test_init_with_invalid_path(tmp_path: Path) -> None:
    """Test initializing GitRepo with an invalid path.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path
    """
    invalid_path = tmp_path / "nonexistent"
    with pytest.raises(GitError, match="Not a git repository"):
        ArboristRepo(invalid_path)


def test_init_with_non_git_directory(tmp_path: Path) -> None:
    """Test initializing GitRepo with a non-git directory.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path
    """
    with pytest.raises(GitError, match="Not a git repository"):
        ArboristRepo(tmp_path)


def test_get_repo_root(temp_repo: GitRepo) -> None:
    """Test getting repository root.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    assert repo.get_repo_root() == str(temp_repo.working_dir)


def test_get_repo_root_bare_repo(tmp_path: Path) -> None:
    """Test getting repository root with a bare repository.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path
    """
    bare_repo_path = tmp_path / "bare.git"
    Repo.init(bare_repo_path, bare=True)
    repo = ArboristRepo(bare_repo_path)

    with pytest.raises(ValueError, match="does not have a working tree directory"):
        repo.get_repo_root()


def test_is_on_branch(temp_repo: GitRepo) -> None:
    """Test checking current branch.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    assert repo.is_on_branch("main")
    assert not repo.is_on_branch("nonexistent")


def test_heads_property(temp_repo: GitRepo) -> None:
    """Test getting repository heads.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    assert len(repo.heads) == 1
    assert repo.heads[0].name == "main"


def test_get_branch_status(temp_repo: GitRepo) -> None:
    """Test getting branch status.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    status = repo.get_branch_status()
    assert isinstance(status, dict)
    assert "main" in status


def test_get_merged_branches(temp_repo: GitRepo) -> None:
    """Test getting merged branches.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    merged = repo.get_merged_branches()
    assert isinstance(merged, list)


def test_get_gone_branches(temp_repo: GitRepo) -> None:
    """Test getting gone branches.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    gone = repo.get_gone_branches()
    assert isinstance(gone, list)


def test_clean_with_dry_run(temp_repo: GitRepo) -> None:
    """Test cleaning branches with dry run.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    repo.clean(dry_run=True)  # Should not modify anything


def test_clean_with_protection(temp_repo: GitRepo) -> None:
    """Test cleaning branches with protection patterns.

    Parameters
    ----------
    temp_repo : GitRepo
        Temporary git repository
    """
    repo = ArboristRepo(temp_repo.working_dir)
    repo.clean(protect=["main", "release-*"])  # Should protect matching branches
