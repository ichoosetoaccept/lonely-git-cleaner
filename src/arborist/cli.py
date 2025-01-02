"""Command line interface for arborist."""

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from arborist.exceptions import GitError
from arborist.git.repo import GitRepo

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Git branch management tool")
console = Console()


def _handle_git_error(err: GitError, exit_code: int = 1) -> None:
    """Handle git errors by printing them and exiting.

    Parameters
    ----------
    err : GitError
        The error to handle
    exit_code : int
        The exit code to use
    """
    print(f"Error: {err}")
    sys.exit(exit_code)


def _validate_branch_name(branch_name: str) -> None:
    """Validate a branch name.

    Parameters
    ----------
    branch_name : str
        The branch name to validate

    Raises
    ------
    typer.BadParameter
        If the branch name is invalid
    """
    if not branch_name:
        raise typer.BadParameter("Branch name cannot be empty")
    if "/" in branch_name and not branch_name.startswith("feature/"):
        raise typer.BadParameter("Branch names with '/' must start with 'feature/'")
    if branch_name.startswith("."):
        raise typer.BadParameter("Branch names cannot start with '.'")
    if branch_name.endswith("/"):
        raise typer.BadParameter("Branch names cannot end with '/'")
    if ".." in branch_name:
        raise typer.BadParameter("Branch names cannot contain '..'")
    if " " in branch_name:
        raise typer.BadParameter("Branch names cannot contain spaces")
    if "~" in branch_name or "^" in branch_name or ":" in branch_name:
        raise typer.BadParameter("Branch names cannot contain '~', '^', or ':'")


@app.command()
def list(
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
) -> None:
    """List all branches."""
    try:
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)

        status_dict = repo.get_branch_status()

        # Create table
        table = Table(title="Branches")
        table.add_column("Branch", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Current", style="green")

        # Add rows
        current = repo.get_current_branch_name()
        for branch, state in sorted(status_dict.items()):
            table.add_row(
                branch,
                str(state.name).lower(),
                "✓" if branch == current else "",
            )

        console.print(table)
    except GitError as err:
        _handle_git_error(err)


@app.command()
def clean(
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
    protect: str = typer.Option(
        "", "--protect", "-p", help="Comma-separated list of branch patterns to protect from deletion"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion of unmerged branches"),
    no_interactive: bool = typer.Option(False, "--no-interactive", "-y", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without doing it"),
) -> None:
    """Clean up merged and gone branches."""
    try:
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)
        protect_list = [p.strip() for p in protect.split(",")] if protect else None
        repo.clean(protect_list, force, no_interactive, dry_run)
    except GitError as err:
        _handle_git_error(err)


@app.command(name="delete_branch")
def delete_branch(
    branch_name: Annotated[str, typer.Argument(help="Name of the branch to delete")],
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion of unmerged branches"),
) -> None:
    """Delete a branch."""
    try:
        # Validate branch name
        _validate_branch_name(branch_name)

        # Initialize repo and get status
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)

        status_dict = repo.get_branch_status()

        # Check if branch exists
        if branch_name not in status_dict:
            print(f"Error: Branch '{branch_name}' does not exist")
            sys.exit(1)

        # Check if trying to delete current branch
        if repo.is_on_branch(branch_name):
            print(f"Error: Cannot delete current branch '{branch_name}'")
            sys.exit(1)

        # Delete branch
        repo.delete_branch(branch_name, force)
        print(f"Deleted branch '{branch_name}'")

    except GitError as err:
        _handle_git_error(err)
    except typer.BadParameter as err:
        print(f"Error: {err}")
        sys.exit(1)


@app.command(name="create_branch")
def create_branch(
    branch_name: Annotated[str, typer.Argument(help="Name of the new branch")],
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
    start_point: str = typer.Option(None, "--start-point", "-s", help="Commit or branch to start from"),
) -> None:
    """Create a new branch."""
    try:
        # Validate branch name
        _validate_branch_name(branch_name)

        # Initialize repo
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)

        # Check if branch already exists
        if branch_name in [b.name for b in repo.heads]:
            print(f"Error: Branch '{branch_name}' already exists")
            sys.exit(1)

        # Create branch
        repo.create_branch(branch_name, start_point)
        print(f"Created branch '{branch_name}'")

    except GitError as err:
        _handle_git_error(err)
    except typer.BadParameter as err:
        print(f"Error: {err}")
        sys.exit(1)


@app.command()
def switch(
    branch_name: Annotated[str, typer.Argument(help="Name of the branch to switch to")],
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
) -> None:
    """Switch to a branch."""
    try:
        # Validate branch name
        _validate_branch_name(branch_name)

        # Initialize repo
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)

        # Check if branch exists
        if branch_name not in [b.name for b in repo.heads]:
            print(f"Error: Branch '{branch_name}' does not exist")
            sys.exit(1)

        # Switch branch
        repo.switch_branch(branch_name)
        print(f"Switched to branch '{branch_name}'")

    except GitError as err:
        _handle_git_error(err)
    except typer.BadParameter as err:
        print(f"Error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    app()
