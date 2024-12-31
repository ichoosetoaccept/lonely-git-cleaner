"""Git command execution module."""

from pathlib import Path
from subprocess import PIPE, Popen

from arborist.exceptions import GitError


def run_git_command(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return its output.

    Parameters
    ----------
    args : list[str]
        Command arguments.
    cwd : Optional[Path]
        Working directory.

    Returns
    -------
    str
        Command output.

    Raises
    ------
    GitError
        If the command fails.
    """
    try:
        with Popen(["git", *args], stdout=PIPE, stderr=PIPE, cwd=cwd) as proc:
            try:
                stdout, stderr = proc.communicate(timeout=30)
            except TimeoutError:
                proc.kill()
                raise GitError("Command timed out") from None
            if proc.returncode != 0:
                raise GitError(stderr.decode()) from None
            return stdout.decode()
    except Exception as err:
        raise GitError(f"Failed to run git command: {err}") from err


def get_current_branch() -> str:
    """Get current branch name.

    Returns
    -------
    str
        Current branch name.

    Raises
    ------
    GitError
        If the command fails.
    """
    try:
        return run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    except GitError as err:
        raise GitError("Failed to get current branch") from err


def get_protected_branches(patterns: list[str] | None = None) -> list[str]:
    """Get list of protected branch names.

    Parameters
    ----------
    patterns : Optional[List[str]]
        List of protected branch patterns.

    Returns
    -------
    List[str]
        List of protected branch names.

    Raises
    ------
    GitError
        If the command fails.
    """
    if patterns is None:
        patterns = ["main", "master", "develop", "release/*"]

    try:
        branches = run_git_command(["branch", "--list"]).splitlines()
        protected = []
        for branch in branches:
            branch_name = branch.strip().lstrip("* ")
            for pattern in patterns:
                if pattern.endswith("*"):
                    if branch_name.startswith(pattern[:-1]):
                        protected.append(branch_name)
                elif branch_name == pattern:
                    protected.append(branch_name)
        return protected
    except GitError as err:
        raise GitError("Failed to get protected branches") from err


def get_remote_branches() -> list[str]:
    """Get list of remote branch names.

    Returns
    -------
    List[str]
        List of remote branch names.

    Raises
    ------
    GitError
        If the command fails.
    """
    try:
        output = run_git_command(["branch", "-r"]).splitlines()
        branches = []
        for line in output:
            branch = line.strip()
            if branch and not branch.endswith("/HEAD"):
                branch = branch.split("/", 1)[1]
                branches.append(branch)
        return sorted(branches)
    except GitError as err:
        raise GitError("Failed to get remote branches") from err


def delete_branch(branch_name: str, force: bool = False) -> None:
    """Delete a local branch.

    Parameters
    ----------
    branch_name : str
        Name of the branch to delete.
    force : bool
        Whether to force delete the branch.

    Raises
    ------
    GitError
        If the command fails.
    """
    try:
        args = ["branch", "-D" if force else "-d", branch_name]
        run_git_command(args)
    except GitError as err:
        raise GitError(f"Failed to delete branch {branch_name}") from err


def delete_remote_branch(branch_name: str) -> None:
    """Delete a remote branch.

    Parameters
    ----------
    branch_name : str
        Name of the branch to delete.

    Raises
    ------
    GitError
        If the command fails.
    """
    try:
        run_git_command(["push", "origin", "--delete", branch_name])
    except GitError as err:
        raise GitError(f"Failed to delete remote branch {branch_name}") from err
