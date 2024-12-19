"""Git operations for branch cleanup."""

import subprocess
from collections.abc import Callable
from pathlib import Path


class GitError(Exception):
    """Base exception for git operations."""

    pass


def run_git_command(
    command: list[str],
    silent: bool = False,
    check: bool = True,
) -> tuple[str, str]:
    """Run a git command and return stdout and stderr."""
    try:
        result = subprocess.run(
            ["git", *command],
            capture_output=True,
            text=True,
            check=check,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        if not silent:
            raise GitError(f"Git command failed: {e.stderr}") from e
        return "", e.stderr.strip()


def is_git_repo() -> bool:
    """Check if current directory is a git repository."""
    stdout, stderr = run_git_command(
        ["rev-parse", "--is-inside-work-tree"],
        silent=True,
        check=False,
    )
    return not stderr and stdout == "true"


def get_gone_branches() -> list[str]:
    """Get list of branches whose remotes are gone."""
    stdout, _ = run_git_command(["branch", "-vv"])
    gone_branches = []

    for line in stdout.splitlines():
        if ": gone]" in line:
            # Extract branch name from the line
            branch = line.strip().split()[0]
            gone_branches.append(branch)

    return gone_branches


def get_merged_branches() -> list[str]:
    """Get list of merged branches."""
    stdout, _ = run_git_command(["branch", "--merged"])
    merged_branches = []

    for line in stdout.splitlines():
        branch = line.strip()
        # Skip current branch (marked with *)
        if branch and not branch.startswith("*"):
            merged_branches.append(branch.strip())

    return merged_branches


def delete_branch(branch: str, force: bool = False) -> None:
    """Delete a git branch."""
    command = ["branch", "-D" if force else "-d", branch]
    run_git_command(command)


def optimize_repo(progress_callback: Callable[[str], None] | None = None) -> None:
    """Run git gc and prune operations."""
    # Remove any existing gc.log
    try:
        Path(".git/gc.log").unlink(missing_ok=True)
    except OSError:
        pass

    # Run prune
    if progress_callback:
        progress_callback("Pruning unreachable objects...")
    run_git_command(["prune"])

    # Run garbage collection
    if progress_callback:
        progress_callback("Running garbage collection...")
    run_git_command(["gc"])

    if progress_callback:
        progress_callback("Repository optimization complete")


def fetch_and_prune(progress_callback: Callable[[str], None] | None = None) -> None:
    """Fetch from remotes and prune."""
    if progress_callback:
        progress_callback("Fetching from remotes...")
    run_git_command(["fetch", "-p"])
    if progress_callback:
        progress_callback("Pruning old references...")


def filter_protected_branches(branches: list[str], protected: list[str]) -> list[str]:
    """Filter out protected branches from the list."""
    return [b for b in branches if b not in protected]
