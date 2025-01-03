"""Common git functionality."""

import logging
import re
from enum import Enum, auto
from typing import Dict, List, Union

from git import GitCommandError, Repo
from git.refs import Head

from arborist.errors import ErrorCode, GitError

# Type aliases
BranchName = str
BranchDict = Dict[str, "BranchStatus"]
BranchList = List[str]

# Branch name validation pattern
BRANCH_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9/_.-]*[a-zA-Z0-9]$")
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
    """Validate that a branch name is valid.

    Parameters
    ----------
    branch_name : str
        The name of the branch to validate

    Raises
    ------
    GitError
        If the branch name is invalid
    """
    # Check for empty branch name
    if not branch_name:
        raise GitError(
            "Branch name cannot be empty",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names must contain at least one character",
        )

    # Check for invalid start/end characters
    if branch_name.startswith(("-", "/")) or branch_name.endswith(("-", "/")):
        raise GitError(
            f"Branch name '{branch_name}' is invalid",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names cannot start or end with hyphens or slashes",
        )

    # Check for double slashes
    if "//" in branch_name:
        raise GitError(
            f"Branch name '{branch_name}' contains double slashes",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names cannot contain consecutive forward slashes",
        )

    # Check for invalid characters
    invalid_chars = [" ", "~", "^", ":", "?", "*", "[", "\\"]
    if any(char in branch_name for char in invalid_chars):
        found_chars = [char for char in invalid_chars if char in branch_name]
        raise GitError(
            f"Branch name '{branch_name}' contains invalid characters",
            code=ErrorCode.BRANCH_ERROR,
            details=f"Found invalid characters: {', '.join(repr(c) for c in found_chars)}",
        )

    # Check for control characters
    if any(ord(char) < 32 or ord(char) == 127 for char in branch_name):
        raise GitError(
            f"Branch name '{branch_name}' contains control characters",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names cannot contain control characters",
        )

    # Check for leading or trailing dots
    if branch_name.startswith(".") or branch_name.endswith("."):
        raise GitError(
            f"Branch name '{branch_name}' has leading or trailing dots",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names cannot start or end with dots",
        )

    # Check for @{
    if "@{" in branch_name:
        raise GitError(
            f"Branch name '{branch_name}' contains '@{{' sequence",
            code=ErrorCode.BRANCH_ERROR,
            details="Branch names cannot contain '@{' sequence",
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
        raise GitError(f"Failed to get commit SHA for branch '{branch_name}': {err}") from err


def is_branch_upstream_of_another(
    repo: Repo, upstream_branch_name: BranchName, downstream_branch_name: BranchName
) -> bool:
    """Check if one branch is merged into another.

    This checks if all changes from upstream_branch are present in downstream_branch,
    regardless of whether it was merged directly or via squash merge.

    Parameters
    ----------
    repo : Repo
        GitPython repository instance
    upstream_branch_name : str
        The name of the branch to check if merged
    downstream_branch_name : str
        The name of the branch to check if merged into

    Returns
    -------
    bool
        True if all changes from upstream_branch are in downstream_branch

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

        # If they're the same commit, definitely merged
        if upstream_commit == downstream_commit:
            return True

        # Find the merge base (common ancestor)
        merge_base = repo.merge_base(upstream_commit, downstream_commit)
        if not merge_base:
            return False

        # If merge base is the same as upstream commit, it means upstream is behind
        # downstream and thus is considered merged
        if merge_base[0] == upstream_commit:
            return True

        # Otherwise, check if there are any changes in upstream that aren't in downstream
        diffs = upstream_commit.diff(downstream_commit)
        return len(diffs) == 0

    except GitCommandError as err:
        raise GitError(
            f"Failed to check if '{upstream_branch_name}' is merged into " f"'{downstream_branch_name}': {err}"
        ) from err
