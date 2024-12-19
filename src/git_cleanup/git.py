"""Git operations for branch cleanup."""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class GitError(Exception):
    """Base exception for git operations."""
    pass


def run_git_command(
    command: List[str],
    silent: bool = False,
    check: bool = True
) -> Tuple[str, str]:
    """Run a git command and return stdout and stderr."""
    try:
        result = subprocess.run(
            ["git"] + command,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        if not silent:
            raise GitError(f"Git command failed: {e.stderr}") from e
        return "", e.stderr.strip()


def is_git_repo() -> bool:
    """Check if current directory is a git repository."""
    stdout, stderr = run_git_command(["rev-parse", "--is-inside-work-tree"], silent=True, check=False)
    return not stderr and stdout == "true"


def get_gone_branches() -> List[str]:
    """Get list of branches whose remotes are gone."""
    stdout, _ = run_git_command(["branch", "-vv"])
    gone_branches = []
    
    for line in stdout.splitlines():
        if ": gone]" in line:
            # Extract branch name from the line
            branch = line.strip().split()[0]
            gone_branches.append(branch)
    
    return gone_branches


def get_merged_branches() -> List[str]:
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


def optimize_repo() -> None:
    """Run git gc and prune operations."""
    # Remove any existing gc.log
    try:
        Path(".git/gc.log").unlink(missing_ok=True)
    except OSError:
        pass

    # Run prune
    run_git_command(["prune"])
    
    # Run garbage collection
    run_git_command(["gc"])


def fetch_and_prune() -> None:
    """Fetch from remotes and prune."""
    run_git_command(["fetch", "-p"])


def filter_protected_branches(branches: List[str], protected: List[str]) -> List[str]:
    """Filter out protected branches from the list."""
    return [b for b in branches if b not in protected]
