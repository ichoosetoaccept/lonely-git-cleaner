"""Git operations for arborist using GitPython."""

from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


class GitError(Exception):
    """Git operation error."""

    pass


def get_repo(path: Path | None = None) -> Repo:
    """Get GitPython repository object.

    Parameters
    ----------
    path : Optional[Path]
        Path to repository, defaults to current directory

    Returns
    -------
    Repo
        GitPython repository object

    Raises
    ------
    GitError
        If path is not a git repository

    """
    try:
        return Repo(path or Path.cwd())
    except InvalidGitRepositoryError as e:
        raise GitError("Not a git repository") from e


def is_git_repo(path: Path | None = None) -> bool:
    """Check if path is a Git repository.

    Parameters
    ----------
    path : Optional[Path]
        Path to check, defaults to current directory

    Returns
    -------
    bool
        True if path is a git repository

    """
    try:
        get_repo(path)
        return True
    except GitError:
        return False


def has_remote(repo: Repo | None = None) -> bool:
    """Check if repository has a remote named 'origin'.

    Parameters
    ----------
    repo : Optional[Repo]
        Repository to check, defaults to current directory

    Returns
    -------
    bool
        True if repository has remote named 'origin'

    """
    try:
        repo = repo or get_repo()
        return "origin" in repo.remotes
    except GitError:
        return False


def get_gone_branches(repo: Repo | None = None) -> list[str]:
    """Find local branches whose remote tracking branches are gone.

    Parameters
    ----------
    repo : Optional[Repo]
        Repository to check, defaults to current directory

    Returns
    -------
    List[str]
        List of branch names whose remote tracking branches are gone

    """
    try:
        repo = repo or get_repo()
        if not has_remote(repo):
            return []

        print("\nDebug: get_gone_branches")
        print(f"Current branch: {repo.active_branch.name}")
        print(f"All branches: {[b.name for b in repo.heads]}")
        print(f"Remote branches: {[ref.name for ref in repo.remotes.origin.refs]}")

        # Fetch and prune to ensure remote state is up to date
        try:
            repo.remote().fetch(prune=True)
        except GitCommandError as e:
            print(f"Fetch error: {e}")
            return []

        gone_branches = []
        for branch in repo.heads:
            tracking = branch.tracking_branch()
            print(f"Checking branch {branch.name}: tracking={tracking}")
            if tracking and not tracking.is_valid():
                gone_branches.append(branch.name)

        print(f"Gone branches: {gone_branches}")
        return gone_branches
    except GitError:
        return []


def delete_branch(branch: str, force: bool = False, repo: Repo | None = None) -> None:
    """Delete a local branch.

    Parameters
    ----------
    branch : str
        Name of branch to delete
    force : bool
        Force delete even if not merged
    repo : Optional[Repo]
        Repository to operate on, defaults to current directory

    Raises
    ------
    GitError
        If branch deletion fails

    """
    try:
        repo = repo or get_repo()
        if branch not in repo.heads:
            raise GitError(f"Branch {branch} does not exist")

        branch_ref = repo.heads[branch]
        if branch_ref.is_current:
            raise GitError("Cannot delete current branch")

        try:
            repo.delete_head(branch_ref, force=force)
        except GitCommandError as e:
            raise GitError(f"Failed to delete branch {branch}: {e!s}") from e
    except GitError as e:
        raise GitError(f"Failed to delete branch {branch}") from e


def delete_remote_branch(branch: str, repo: Repo | None = None) -> None:
    """Delete a remote branch.

    Parameters
    ----------
    branch : str
        Name of branch to delete
    repo : Optional[Repo]
        Repository to operate on, defaults to current directory

    Raises
    ------
    GitError
        If branch deletion fails

    """
    try:
        repo = repo or get_repo()
        if not has_remote(repo):
            raise GitError("No remote repository")

        remote = repo.remote()
        try:
            remote.push(refspec=f":{branch}")
        except GitCommandError as e:
            raise GitError(f"Failed to delete remote branch {branch}: {e!s}") from e
    except GitError as e:
        raise GitError(f"Failed to delete remote branch {branch}") from e


def optimize_repo(repo: Repo | None = None) -> None:
    """Run git gc to optimize the repository.

    Parameters
    ----------
    repo : Optional[Repo]
        Repository to optimize, defaults to current directory

    Raises
    ------
    GitError
        If optimization fails

    """
    try:
        repo = repo or get_repo()
        try:
            repo.git.gc()
        except GitCommandError as e:
            raise GitError(f"Failed to optimize repository: {e!s}") from e
    except GitError as e:
        raise GitError("Failed to optimize repository") from e


def get_merged_branches(
    target: str | None = None, repo: Repo | None = None
) -> list[str]:
    """Get list of branches that are merged into target.

    Parameters
    ----------
    target : Optional[str]
        Target branch to check against. If None, uses current branch.
    repo : Optional[Repo]
        Repository to check, defaults to current directory

    Returns
    -------
    List[str]
        List of merged branch names

    Raises
    ------
    GitError
        If target branch does not exist

    """
    try:
        repo = repo or get_repo()
        if target is None:
            target = repo.active_branch.name
        elif target not in repo.heads:
            raise GitError(f"Target branch {target} does not exist")

        print("\nDebug: get_merged_branches")
        print(f"Current branch: {repo.active_branch.name}")
        print(f"Target branch: {target}")
        print(f"All branches: {[b.name for b in repo.heads]}")

        # Get list of merged branches using git command
        try:
            output = repo.git.branch("--merged", target)
            print(f"Git branch --merged output:\n{output}")
            merged = []
            for line in output.splitlines():
                branch_name = line.strip().lstrip("* ")
                if branch_name and branch_name != target:
                    merged.append(branch_name)
            print(f"Merged branches: {merged}")
        except GitCommandError as e:
            print(f"Git command error: {e}")
            # Fall back to using is_ancestor if git branch --merged fails
            target_commit = repo.heads[target].commit
            merged = []
            for branch in repo.heads:
                if branch.name == target:
                    continue
                if repo.is_ancestor(branch.commit, target_commit):
                    merged.append(branch.name)
            print(f"Merged branches (using is_ancestor): {merged}")

        return merged
    except GitError as e:
        raise GitError(f"Failed to get merged branches: {e!s}") from e


def filter_protected_branches(branches: list[str], protected: list[str]) -> list[str]:
    """Filter out protected branches from list.

    Parameters
    ----------
    branches : List[str]
        List of branch names to filter
    protected : List[str]
        List of protected branch names

    Returns
    -------
    List[str]
        Filtered list of branch names

    """
    return [b for b in branches if b not in protected]


def create_branch(branch: str) -> None:
    """Create a new branch.

    Parameters
    ----------
    branch : str
        Name of the branch to create.

    Raises
    ------
    GitError
        If the branch creation fails.

    """
    try:
        repo = get_repo()
        repo.git.checkout("-b", branch)
    except Exception as e:
        raise GitError(f"Failed to create branch {branch}: {e}") from e


def _get_merged_remote_branches_via_command(repo: Repo, target: str) -> list[str]:
    """Get merged remote branches using git branch -r --merged command.

    Parameters
    ----------
    repo : Repo
        Repository to check
    target : str
        Target branch to check against

    Returns
    -------
    List[str]
        List of merged remote branch names
    """
    output = repo.git.branch("-r", "--merged", target)
    merged = []
    for line in output.splitlines():
        branch_name = line.strip()
        if not branch_name:
            continue
        # Extract remote branch name without remote prefix
        remote_head = (
            branch_name.split("/", 1)[1] if "/" in branch_name else branch_name
        )
        # Skip the target branch's remote tracking branch and HEAD
        if remote_head in {target, "HEAD"}:
            continue
        merged.append(remote_head)
    return merged


def _get_merged_remote_branches_via_ancestry(repo: Repo, target: str) -> list[str]:
    """Get merged remote branches by checking ancestry.

    Parameters
    ----------
    repo : Repo
        Repository to check
    target : str
        Target branch to check against

    Returns
    -------
    List[str]
        List of merged remote branch names
    """
    merged = []
    target_commit = repo.heads[target].commit
    for ref in repo.remotes.origin.refs:
        remote_head = ref.remote_head
        # Skip the target branch's remote tracking branch and HEAD
        if remote_head in {target, "HEAD"}:
            continue
        # Check if branch is merged
        if repo.is_ancestor(ref.commit, target_commit):
            merged.append(remote_head)
    return merged


def get_merged_remote_branches(
    target: str | None = None, repo: Repo | None = None
) -> list[str]:
    """Get list of remote branches that are merged into target.

    Parameters
    ----------
    target : Optional[str]
        Target branch to check against. If None, uses current branch.
    repo : Optional[Repo]
        Repository to check, defaults to current directory

    Returns
    -------
    List[str]
        List of merged remote branch names

    Raises
    ------
    GitError
        If target branch does not exist
    """
    try:
        repo = repo or get_repo()
        if target is None:
            target = repo.active_branch.name
        elif target not in repo.heads:
            raise GitError(f"Target branch {target} does not exist")

        try:
            return _get_merged_remote_branches_via_command(repo, target)
        except GitCommandError:
            return _get_merged_remote_branches_via_ancestry(repo, target)
    except GitError as e:
        raise GitError(f"Failed to get merged remote branches: {e!s}") from e
