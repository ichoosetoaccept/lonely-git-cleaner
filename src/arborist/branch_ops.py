"""Branch operations for arborist."""

from arborist.exceptions import GitError
from arborist.git.repo import GitRepo


def get_current_branch(repo: GitRepo) -> str:
    """Get the current branch name.

    Parameters
    ----------
    repo : GitRepo
        Repository instance

    Returns
    -------
    str
        Current branch name

    Raises
    ------
    GitError
        If current branch cannot be determined
    """
    try:
        return repo.repo.active_branch.name
    except Exception as err:
        raise GitError("Failed to get current branch") from err


def get_protected_branches(
    repo: GitRepo, patterns: list[str] | None = None
) -> list[str]:
    """Get list of protected branches.

    Parameters
    ----------
    repo : GitRepo
        Repository instance
    patterns : Optional[List[str]]
        List of branch patterns to protect

    Returns
    -------
    List[str]
        List of protected branch names
    """
    if patterns is None:
        patterns = ["main", "master", "develop"]

    protected = []
    for branch in repo.repo.heads:
        if any(branch.name.startswith(pattern) for pattern in patterns):
            protected.append(branch.name)
    return protected


def get_remote_branches(repo: GitRepo) -> list[str]:
    """Get list of remote branches.

    Parameters
    ----------
    repo : GitRepo
        Repository instance

    Returns
    -------
    List[str]
        List of remote branch names
    """
    try:
        if not repo.repo.remotes:
            return []

        remote = repo.repo.remote()
        remote.fetch()
        return [ref.name for ref in remote.refs]
    except Exception as err:
        raise GitError("Failed to get remote branches") from err


def delete_branch(repo: GitRepo, branch_name: str, force: bool = False) -> None:
    """Delete a local branch.

    Parameters
    ----------
    repo : GitRepo
        Repository instance
    branch_name : str
        Name of the branch to delete
    force : bool
        Whether to force deletion of unmerged branches

    Raises
    ------
    GitError
        If branch cannot be deleted
    """
    try:
        repo.delete_branch(branch_name, force=force)
    except GitError as err:
        raise GitError(f"Failed to delete branch {branch_name}: {err}") from err


def delete_remote_branch(repo: GitRepo, branch_name: str) -> None:
    """Delete a remote branch.

    Parameters
    ----------
    repo : GitRepo
        Repository instance
    branch_name : str
        Name of the branch to delete

    Raises
    ------
    GitError
        If branch cannot be deleted
    """
    try:
        repo.delete_remote_branch(branch_name)
    except GitError as err:
        raise GitError(f"Failed to delete remote branch {branch_name}: {err}") from err
