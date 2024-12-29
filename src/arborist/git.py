"""Git operations for arborist."""

import subprocess
from pathlib import Path


def run_git_command(
    args: list[str],
    silent: bool = False,
    cwd: Path | None = None,
) -> tuple[str, str]:
    """Run a Git command and return its output.

    Parameters
    ----------
    args : list[str]
        Command arguments to pass to Git.
    silent : bool, optional
        Whether to suppress error output, by default False.
    cwd : Optional[Path], optional
        Working directory to run the command in, by default None.

    Returns
    -------
    tuple[str, str]
        A tuple of (stdout, stderr) from the command.

    Raises
    ------
    GitError
        If the command fails and silent is False.

    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        if not silent:
            raise GitError(f"Git command failed: {e.stderr}") from e
        return "", e.stderr.strip()


class GitError(Exception):
    """Git operation error."""

    pass


def is_git_repo() -> bool:
    """Check if current directory is a Git repository."""
    try:
        stdout, stderr = run_git_command(["rev-parse", "--git-dir"], silent=True)
        return not stderr and stdout
    except GitError:
        return False


def get_gone_branches() -> list[str]:
    """Find local branches whose remote tracking branches are gone.

    Returns
    -------
    list[str]
        List of branch names whose remote tracking branches are gone.

    """
    # Fetch and prune first to ensure remote state is up to date
    fetch_and_prune()

    # Get list of branches with [gone] status
    stdout, _ = run_git_command(["branch", "-vv"])
    gone_branches = []

    for line in stdout.splitlines():
        # Format is "  branch-name hash [origin/branch-name: gone] message"
        # or "* branch-name hash [origin/branch-name: gone] message"
        if ": gone]" in line:  # Changed from "[gone]" to ": gone]"
            parts = line.strip().split()
            branch_name = parts[0] if parts[0] != "*" else parts[1]
            gone_branches.append(branch_name)

    return gone_branches


def delete_branch(branch: str, force: bool = False) -> None:
    """Delete a local branch.

    Parameters
    ----------
    branch : str
        Name of the branch to delete.
    force : bool, optional
        Whether to force delete the branch, by default False.

    Raises
    ------
    GitError
        If the branch deletion fails.

    """
    try:
        # Get current branch
        current_stdout, _ = run_git_command(["branch", "--show-current"])
        current_branch = current_stdout.strip()

        # Switch to main if we're on the branch to be deleted
        if current_branch == branch:
            run_git_command(["checkout", "main"])

        # Try to delete the branch
        try:
            run_git_command(["branch", "-D" if force else "-d", branch])
        except GitError as e:
            if not force and "not fully merged" in str(e):
                # Branch is not merged, try force delete
                run_git_command(["branch", "-D", branch])
            else:
                raise
    except GitError as e:
        raise GitError(f"Failed to delete branch {branch}: {e}") from e


def delete_remote_branch(branch: str) -> None:
    """Delete a remote branch.

    Parameters
    ----------
    branch : str
        Name of the branch to delete.

    Raises
    ------
    GitError
        If the branch deletion fails.

    """
    try:
        run_git_command(["push", "origin", "--delete", branch])
    except GitError as e:
        raise GitError(f"Failed to delete remote branch {branch}: {e}") from e


def optimize_repo() -> None:
    """Optimize the repository by running garbage collection."""
    try:
        run_git_command(["gc", "--prune=now"])
    except GitError as e:
        raise GitError(f"Failed to optimize repository: {e}") from e


def fetch_and_prune() -> None:
    """Fetch from remote and prune deleted branches."""
    try:
        run_git_command(["fetch", "--prune", "origin"])
    except GitError as e:
        raise GitError(f"Failed to fetch and prune: {e}") from e


def get_merged_branches(target: str = "main") -> list[str]:
    """Get list of branches merged into target.

    Parameters
    ----------
    target : str, optional
        Target branch to check against, by default "main".

    Returns
    -------
    list[str]
        List of merged branch names.

    """
    stdout, _ = run_git_command(["branch", "--merged", target])
    return [
        b.strip()
        for b in stdout.splitlines()
        if b.strip() and not b.strip().startswith("*")
    ]


def get_merged_remote_branches() -> list[str]:
    """Get list of remote branches that have been merged.

    Returns
    -------
    list[str]
        List of merged remote branch names.

    """
    # Get current branch
    current_branch, _ = run_git_command(["branch", "--show-current"])
    current_branch = current_branch.strip()

    # Get list of merged branches
    stdout, _ = run_git_command(["branch", "-r", "--merged"])
    merged_branches = []

    for line in stdout.splitlines():
        branch = line.strip()
        if branch.startswith("origin/") and not branch.endswith("/HEAD"):
            # Remove "origin/" prefix
            branch_name = branch[7:]
            if branch_name != current_branch:
                merged_branches.append(branch_name)

    return merged_branches


def filter_protected_branches(branches: list[str], protected: list[str]) -> list[str]:
    """Filter out protected branches from a list of branches.

    Parameters
    ----------
    branches : list[str]
        List of branch names to filter.
    protected : list[str]
        List of protected branch names.

    Returns
    -------
    list[str]
        List of branch names that are not protected.

    """
    return [b for b in branches if b not in protected]


def create_branch(branch: str) -> None:
    """Create a new Git branch.

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
        run_git_command(["checkout", "-b", branch])
    except GitError as e:
        raise GitError(f"Failed to create branch {branch}: {e}") from e
