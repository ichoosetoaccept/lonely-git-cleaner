"""Common git functionality."""

import logging
import re
from enum import Enum, auto
from typing import Dict, List, Union

from git import GitCommandError, Repo
from git.refs import Head

from arborist.exceptions import GitError

# Type aliases
BranchName = str
BranchDict = Dict[str, "BranchStatus"]
BranchList = List[str]

# Branch name validation pattern
BRANCH_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9/_-]*[a-zA-Z0-9]$")
INVALID_BRANCH_CHARS = {"~", "^", ":", "\\", " ", "*", "?", "[", "]"}


class BranchStatus(Enum):
    """Branch status enum."""

    MERGED = auto()
    UNMERGED = auto()
    GONE = auto()
    UNKNOWN = auto()


# Set up logging
logger = logging.getLogger(__name__)


def log_git_error(error: Union[GitError, GitCommandError], message: str) -> None:
    """Log a git error with additional context.

    Parameters
    ----------
    error : Union[GitError, GitCommandError]
        The error to log
    message : str
        Additional context message
    """
    logger.error("%s: %s", message, str(error))


def validate_branch_name(branch_name: BranchName) -> None:
    """Validate branch name format.

    Parameters
    ----------
    branch_name : str
        The name of the branch to validate

    Raises
    ------
    GitError
        If the branch name is invalid
    """
    if not branch_name:
        raise GitError("Branch name cannot be empty")

    if any(char in branch_name for char in INVALID_BRANCH_CHARS):
        raise GitError(
            f"Branch name '{branch_name}' contains invalid characters. "
            f"Cannot contain: {', '.join(sorted(INVALID_BRANCH_CHARS))}"
        )

    if not BRANCH_NAME_PATTERN.match(branch_name):
        raise GitError(
            f"Branch name '{branch_name}' is invalid. Must start and end with "
            "alphanumeric characters and contain only alphanumeric characters, "
            "forward slashes, underscores, or hyphens"
        )


def validate_branch_exists(repo: Repo, branch_name: BranchName) -> None:
    """Validate that a branch exists.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    branch_name : str
        The name of the branch to validate

    Raises
    ------
    GitError
        If the branch does not exist
    """
    if branch_name not in repo.heads:
        raise GitError(f"Branch '{branch_name}' does not exist")


def validate_branch_doesnt_exist(repo: Repo, branch_name: BranchName) -> None:
    """Validate that a branch does not exist.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    branch_name : str
        The name of the branch to validate

    Raises
    ------
    GitError
        If the branch already exists
    """
    if branch_name in repo.heads:
        raise GitError(f"Branch '{branch_name}' already exists")


def get_branch(repo: Repo, branch_name: BranchName) -> Head:
    """Get a branch by name.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    branch_name : str
        The name of the branch to get

    Returns
    -------
    Head
        The branch reference

    Raises
    ------
    GitError
        If the branch does not exist
    """
    try:
        return repo.heads[branch_name]
    except IndexError as err:
        raise GitError(f"Branch '{branch_name}' does not exist") from err


def get_current_branch_name(repo: Repo) -> BranchName:
    """Get the name of the currently checked out branch.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance

    Returns
    -------
    str
        The name of the current branch

    Raises
    ------
    GitError
        If the current branch cannot be determined
    """
    try:
        return repo.active_branch.name
    except (TypeError, GitCommandError) as err:
        raise GitError("Failed to determine current branch") from err


def get_latest_commit_sha(repo: Repo, branch_name: BranchName) -> str:
    """Get the latest commit SHA for the given branch.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    branch_name : str
        The name of the branch

    Returns
    -------
    str
        The commit SHA

    Raises
    ------
    GitError
        If the branch does not exist or the SHA cannot be determined
    """
    try:
        validate_branch_name(branch_name)
        validate_branch_exists(repo, branch_name)
        return repo.branches[branch_name].commit.hexsha
    except (IndexError, GitCommandError) as err:
        raise GitError(
            f"Failed to get commit SHA for branch '{branch_name}': {err}"
        ) from err


def is_branch_upstream_of_another(
    repo: Repo, upstream_branch_name: BranchName, downstream_branch_name: BranchName
) -> bool:
    """Check if one branch is upstream of another.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    upstream_branch_name : str
        The name of the potential upstream branch
    downstream_branch_name : str
        The name of the potential downstream branch

    Returns
    -------
    bool
        True if upstream_branch is an ancestor of downstream_branch

    Raises
    ------
    GitError
        If either branch does not exist
    """
    try:
        validate_branch_name(upstream_branch_name)
        validate_branch_name(downstream_branch_name)
        validate_branch_exists(repo, upstream_branch_name)
        validate_branch_exists(repo, downstream_branch_name)
        upstream_commit = repo.branches[upstream_branch_name].commit
        downstream_commit = repo.branches[downstream_branch_name].commit
        return repo.is_ancestor(upstream_commit, downstream_commit)
    except GitCommandError as err:
        raise GitError(
            f"Failed to check if '{upstream_branch_name}' is upstream of "
            f"'{downstream_branch_name}': {err}"
        ) from err
