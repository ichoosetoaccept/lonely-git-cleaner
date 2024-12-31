"""Command line interface for arborist."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from arborist.exceptions import GitError
from arborist.git.repo import GitRepo

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
    print(f"[red]Error:[/red] {err}")
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


# Define common options
PathOption = Annotated[
    Path | None,
    typer.Option(None, help="Path to git repository. Defaults to current directory."),
]


@app.command()
def status(
    path: Annotated[
        Path | None,
        typer.Argument(
            None, help="Path to git repository. Defaults to current directory."
        ),
    ] = None,
) -> None:
    """Show status of all branches."""
    try:
        repo = GitRepo(path)
        status_dict = repo.get_branch_status()

        # Create table
        table = Table(title="Branch Status")
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
def delete_branch(
    branch_name: Annotated[
        str, typer.Argument(..., help="Name of the branch to delete")
    ],
    force: Annotated[
        bool,
        typer.Option(
            False, "--force", "-f", help="Force deletion of unmerged branches"
        ),
    ] = False,
    path: PathOption = None,
) -> None:
    """Delete a branch."""
    try:
        # Validate branch name
        _validate_branch_name(branch_name)

        # Initialize repo and get status
        repo = GitRepo(path)
        status_dict = repo.get_branch_status()

        # Check if branch exists
        if branch_name not in status_dict:
            print(f"[red]Error:[/red] Branch '{branch_name}' does not exist")
            sys.exit(1)

        # Check if trying to delete current branch
        if repo.is_on_branch(branch_name):
            print(f"[red]Error:[/red] Cannot delete current branch '{branch_name}'")
            sys.exit(1)

        # Delete branch
        repo.delete_branch(branch_name, force)
        print(f"[green]Deleted branch:[/green] {branch_name}")

    except GitError as err:
        _handle_git_error(err)
    except typer.BadParameter as err:
        print(f"[red]Error:[/red] {err}")
        sys.exit(1)


@app.command()
def clean(
    protect: Annotated[
        list[str] | None,
        typer.Option(
            None,
            "--protect",
            "-p",
            help="Branch patterns to protect from deletion",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            False, "--force", "-f", help="Force deletion of unmerged branches"
        ),
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option(False, "--no-interactive", "-y", help="Skip confirmation prompts"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            False, "--dry-run", "-n", help="Show what would be done without doing it"
        ),
    ] = False,
    path: PathOption = None,
) -> None:
    """Clean up merged and gone branches."""
    try:
        repo = GitRepo(path)
        repo.clean(protect, force, no_interactive, dry_run)

    except GitError as err:
        _handle_git_error(err)


@app.command()
def create_branch(
    branch_name: Annotated[str, typer.Argument(..., help="Name of the new branch")],
    start_point: Annotated[
        str | None,
        typer.Option(
            None, "--start-point", "-s", help="Commit or branch to start from"
        ),
    ] = None,
    path: PathOption = None,
) -> None:
    """Create a new branch."""
    try:
        # Validate branch name
        _validate_branch_name(branch_name)

        # Initialize repo
        repo = GitRepo(path)

        # Check if branch already exists
        if branch_name in [b.name for b in repo.heads]:
            print(f"[red]Error:[/red] Branch '{branch_name}' already exists")
            sys.exit(1)

        # Create branch
        repo.create_branch(branch_name, start_point)
        print(f"[green]Created branch:[/green] {branch_name}")

    except GitError as err:
        _handle_git_error(err)
    except typer.BadParameter as err:
        print(f"[red]Error:[/red] {err}")
        sys.exit(1)


if __name__ == "__main__":
    app()
