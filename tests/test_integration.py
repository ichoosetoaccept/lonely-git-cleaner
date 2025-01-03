"""Integration tests for arborist CLI."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Generator, TypedDict

import pytest
from git import GitCommandError, Repo
from git.repo.base import Repo as GitRepo

logger = logging.getLogger(__name__)


class BranchScenario(TypedDict):
    """Branch scenario configuration."""

    files: list[tuple[str, str]] | tuple[str, str]
    should_merge: bool
    has_remote: bool


def _get_test_scenarios() -> dict[str, BranchScenario]:
    """Get test branch scenarios.

    Returns
    -------
    dict[str, BranchScenario]
        Branch scenarios
    """
    return {
        # Regular merged branch
        "feature/merged": {
            "files": ("merged.txt", "Merged feature"),
            "should_merge": True,  # Should be merged
            "has_remote": False,  # No remote
        },
        # Unmerged branch
        "feature/unmerged": {
            "files": ("unmerged.txt", "Unmerged feature"),
            "should_merge": False,  # Should not be merged
            "has_remote": False,  # No remote
        },
        # Branch with remote tracking
        "feature/remote": {
            "files": ("remote.txt", "Remote feature"),
            "should_merge": True,  # Should be merged
            "has_remote": True,  # Has remote
        },
        # Protected branch pattern
        "release/1.0": {
            "files": ("release.txt", "Release 1.0"),
            "should_merge": True,  # Should be merged
            "has_remote": False,  # No remote
        },
        # Branch with multiple commits
        "feature/multi-commit": {
            "files": [
                ("multi1.txt", "First commit"),
                ("multi2.txt", "Second commit"),
                ("multi3.txt", "Third commit"),
            ],
            "should_merge": True,  # Should be merged
            "has_remote": False,  # No remote
        },
        # Branch with merge conflicts
        "feature/conflicts": {
            "files": ("conflict.txt", "This will conflict"),
            "should_merge": False,  # Should not be merged
            "has_remote": False,  # No remote
        },
        # Branch with remote but deleted upstream
        "feature/gone": {
            "files": ("gone.txt", "Gone feature"),
            "should_merge": False,  # Should not be merged
            "has_remote": True,  # Has remote (initially)
        },
        # Branch with special characters
        "feature/special-chars-#123": {
            "files": ("special.txt", "Special chars"),
            "should_merge": True,  # Should be merged
            "has_remote": False,  # No remote
        },
    }


def _setup_test_branches(repo: GitRepo, repo_path: Path, scenarios: dict[str, BranchScenario]) -> None:
    """Set up test branches in the repository.

    Parameters
    ----------
    repo : GitRepo
        Repository to set up branches in
    repo_path : Path
        Path to repository
    scenarios : dict[str, BranchScenario]
        Branch scenarios to set up
    """
    # Create each branch first
    for branch_name in scenarios:
        repo.create_head(branch_name)

    # Create merge conflict scenario first
    repo.heads["feature/conflicts"].checkout()
    conflict_file = repo_path / "conflict.txt"
    conflict_file.write_text("Conflict branch content")
    repo.index.add([str(conflict_file)])
    repo.index.commit("Add conflict file on feature branch")

    repo.heads.main.checkout()
    conflict_file.write_text("Main branch content")
    repo.index.add([str(conflict_file)])
    repo.index.commit("Add conflict file on main")

    # Now create content for other branches
    for branch_name, scenario in scenarios.items():
        if branch_name == "feature/conflicts":
            continue  # Skip, already handled

        branch = repo.heads[branch_name]
        branch.checkout()

        # Handle multi-commit scenarios
        files = scenario["files"]
        if isinstance(files, list):
            for filename, content in files:
                test_file = repo_path / filename
                test_file.write_text(content)
                repo.index.add([str(test_file)])
                repo.index.commit(f"Add {filename}")
        else:
            filename, content = files
            test_file = repo_path / filename
            test_file.write_text(content)
            repo.index.add([str(test_file)])
            repo.index.commit(f"Add {filename}")

        if scenario["has_remote"]:
            repo.git.push("--set-upstream", "origin", branch_name)


def _merge_test_branches(repo: GitRepo, scenarios: dict[str, BranchScenario]) -> None:
    """Merge test branches into main.

    Parameters
    ----------
    repo : GitRepo
        Repository to merge branches in
    scenarios : dict[str, BranchScenario]
        Branch scenarios to merge
    """
    # Ensure we're on main and it's up to date
    if "main" not in repo.heads:
        raise ValueError("Main branch not found. Repository not properly initialized.")

    repo.heads.main.checkout()
    if repo.heads.main.tracking_branch():
        repo.git.pull("--ff-only")  # Update main if it has a tracking branch

    # Try to merge branches that should be merged
    for branch_name, scenario in scenarios.items():
        if scenario["should_merge"]:
            try:
                # First update the branch to ensure it's up to date
                repo.heads[branch_name].checkout()
                if repo.heads[branch_name].tracking_branch():
                    repo.git.pull("--ff-only")

                # Then merge into main
                repo.heads.main.checkout()
                repo.git.merge(branch_name, no_ff=True)  # Force a merge commit

                # Verify the merge was successful
                if repo.is_ancestor(repo.heads[branch_name].commit, repo.heads.main.commit):
                    logger.debug("Successfully merged %s into main", branch_name)
                else:
                    logger.warning("Failed to merge %s into main", branch_name)

            except GitCommandError as err:
                logger.error("Error merging %s: %s", branch_name, err)
                repo.git.merge("--abort")
                repo.heads.main.checkout()

    # Ensure we push all changes to main
    repo.heads.main.checkout()
    if repo.heads.main.tracking_branch():
        repo.git.push("origin", "main")


@pytest.fixture
def test_repo(temp_repo: Repo) -> Generator[GitRepo, None, None]:
    """Create a test repository with various branch scenarios.

    Parameters
    ----------
    temp_repo : Repo
        Base test repository from conftest.py

    Yields
    ------
    GitRepo
        Test repository with scenarios
    """
    repo = temp_repo
    repo_path = Path(repo.working_dir)

    # Get and set up test scenarios
    scenarios = _get_test_scenarios()
    _setup_test_branches(repo, repo_path, scenarios)
    _merge_test_branches(repo, scenarios)

    # Simulate deleted upstream branch for feature/gone
    repo.git.push("origin", ":feature/gone")  # Delete remote branch
    repo.git.fetch("--prune")  # Update remote tracking info

    # Change working directory to repo
    old_cwd = os.getcwd()
    os.chdir(repo_path)

    yield repo

    # Restore working directory
    os.chdir(old_cwd)


def run_arb(args: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    """Run arb command and return its output.

    Parameters
    ----------
    args : List[str]
        Command arguments
    input_text : Optional[str]
        Text to send to stdin

    Returns
    -------
    Tuple[int, str, str]
        Exit code, stdout, and stderr
    """
    process = subprocess.run(
        ["arb"] + args,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return process.returncode, process.stdout, process.stderr


def test_list_command(test_repo: GitRepo) -> None:
    """Test arb list command.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    exit_code, stdout, stderr = run_arb(["list"])
    assert exit_code == 0
    assert "feature/merged" in stdout
    assert "feature/unmerged" in stdout
    assert "feature/remote" in stdout
    assert "release/1.0" in stdout
    assert "merged" in stdout.lower()
    assert "unmerged" in stdout.lower()


def test_clean_merged_branch(test_repo: GitRepo) -> None:
    """Test cleaning a merged branch without remote tracking.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with auto-yes
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/merged" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/merged" not in [b.name for b in test_repo.heads]


def test_clean_with_force(test_repo: GitRepo) -> None:
    """Test force cleaning branches.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with force and auto-yes
    exit_code, stdout, stderr = run_arb(["clean", "--force", "--no-interactive"])
    assert exit_code == 0
    assert "feature/unmerged" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/unmerged" not in [b.name for b in test_repo.heads]


def test_clean_with_protection(test_repo: GitRepo) -> None:
    """Test branch protection during cleanup.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with protection and auto-yes
    exit_code, stdout, stderr = run_arb(["clean", "--protect", "release/*", "--no-interactive"])
    assert exit_code == 0
    assert "release/1.0" not in stdout

    # Verify protected branch still exists
    assert "release/1.0" in [b.name for b in test_repo.heads]


def test_clean_dry_run(test_repo: GitRepo) -> None:
    """Test dry run mode.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with dry-run
    exit_code, stdout, stderr = run_arb(["clean", "--dry-run"])
    assert exit_code == 0
    assert "Dry run" in stdout
    assert "feature/merged" in stdout

    # Verify no branches were actually deleted
    assert "feature/merged" in [b.name for b in test_repo.heads]


def test_clean_remote_tracking_branch(test_repo: GitRepo) -> None:
    """Test cleaning a branch with remote tracking.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Try to clean without force
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/remote" not in stdout

    # Clean with force
    exit_code, stdout, stderr = run_arb(["clean", "--force", "--no-interactive"])
    assert exit_code == 0
    assert "feature/remote" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/remote" not in [b.name for b in test_repo.heads]


def test_clean_multi_commit_branch(test_repo: GitRepo) -> None:
    """Test cleaning a branch with multiple commits.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with auto-yes
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/multi-commit" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/multi-commit" not in [b.name for b in test_repo.heads]


def test_clean_branch_with_conflicts(test_repo: GitRepo) -> None:
    """Test cleaning a branch that has merge conflicts.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Try to clean without force
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/conflicts" not in stdout  # Should not be suggested for deletion

    # Clean with force
    exit_code, stdout, stderr = run_arb(["clean", "--force", "--no-interactive"])
    assert exit_code == 0
    assert "feature/conflicts" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/conflicts" not in [b.name for b in test_repo.heads]


def test_clean_gone_branch(test_repo: GitRepo) -> None:
    """Test cleaning a branch whose remote was deleted.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Verify branch is marked as gone
    exit_code, stdout, stderr = run_arb(["list"])
    assert exit_code == 0
    assert "feature/gone" in stdout
    assert "gone" in stdout.lower()

    # Clean with auto-yes (gone branches should be cleaned)
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/gone" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/gone" not in [b.name for b in test_repo.heads]


def test_clean_special_chars_branch(test_repo: GitRepo) -> None:
    """Test cleaning a branch with special characters in its name.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Clean with auto-yes
    exit_code, stdout, stderr = run_arb(["clean", "--no-interactive"])
    assert exit_code == 0
    assert "feature/special-chars-#123" in stdout
    assert "Successfully deleted" in stdout

    # Verify branch is gone
    assert "feature/special-chars-#123" not in [b.name for b in test_repo.heads]


def test_clean_interactive_cancel(test_repo: GitRepo) -> None:
    """Test canceling branch cleanup in interactive mode.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Get initial branch list
    initial_branches = {b.name for b in test_repo.heads}

    # Run clean and respond with 'n'
    exit_code, stdout, stderr = run_arb(["clean"], input_text="n")
    assert exit_code == 0
    assert "Operation cancelled" in stdout

    # Verify no branches were deleted
    final_branches = {b.name for b in test_repo.heads}
    assert initial_branches == final_branches


def test_clean_current_branch(test_repo: GitRepo) -> None:
    """Test attempting to clean the current branch.

    Parameters
    ----------
    test_repo : GitRepo
        Test repository
    """
    # Switch to a merged branch
    test_repo.heads["feature/merged"].checkout()

    # Try to clean with force
    exit_code, stdout, stderr = run_arb(["clean", "--force", "--no-interactive"])
    assert exit_code == 0

    # Current branch should be skipped
    assert "feature/merged" in [b.name for b in test_repo.heads]
