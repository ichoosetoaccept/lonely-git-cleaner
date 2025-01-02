"""Command line interface for arborist."""

import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from arborist.errors import GitError
from arborist.git.repo import GitRepo

# Set default logging level to WARNING
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Git branch management tool")
console = Console()


def _set_debug_logging(debug: bool) -> None:
    """Set logging level based on debug flag.

    Parameters
    ----------
    debug : bool
        Whether to enable debug logging
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        # Also enable debug logging for gitpython
        logging.getLogger("git").setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)
        # Disable debug logging for gitpython
        logging.getLogger("git").setLevel(logging.WARNING)


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


@app.command()
def list(
    path: Annotated[Path, typer.Option(help="Path to git repository")] = Path("."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """List all branches with their cleanup status."""
    try:
        _set_debug_logging(debug)
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
        "main", "--protect", "-p", help="Comma-separated list of branch patterns to protect from deletion"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion of unmerged branches"),
    no_interactive: bool = typer.Option(False, "--no-interactive", "-y", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without doing it"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Clean up merged and gone branches."""
    try:
        _set_debug_logging(debug)
        logger.debug(f"Using repository at: {path}")
        repo = GitRepo(path)
        protect_list = [p.strip() for p in protect.split(",")]
        repo.clean(protect_list, force, no_interactive, dry_run)
    except GitError as err:
        _handle_git_error(err)


if __name__ == "__main__":
    app()
