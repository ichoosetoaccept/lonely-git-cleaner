"""Command-line interface for the arborist package."""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from arborist import git
from arborist.config import Config, ConfigError, load_config
from arborist.git import (
    GitError,
    delete_remote_branch,
    filter_protected_branches,
    get_gone_branches,
    get_merged_branches,
    get_merged_remote_branches,
    is_git_repo,
    optimize_repo,
)

# CLI options
NO_INTERACTIVE_OPTION = typer.Option(
    False,
    "--no-interactive",
    help="Run without interactive prompts",
)

DRY_RUN_OPTION = typer.Option(
    None,
    "--dry-run",
    help="Show what would be done without making changes",
)

NO_GC_OPTION = typer.Option(
    None,
    "--no-gc",
    help="Skip repository optimization",
)

PROTECT_OPTION = typer.Option(
    None,
    "--protect",
    help="Additional branches to protect",
)

CONFIG_PATH_OPTION = typer.Option(
    None,
    "--config",
    help="Path to config file",
)

app = typer.Typer(
    help="Clean up git branches that are gone or merged.",
    add_completion=False,
)
console = Console()


def validate_git_repo() -> None:
    """Validate we're in a git repository."""
    if not is_git_repo():
        console.print("[red]Error: Not a git repository[/red]")
        raise typer.Exit(code=1)


def handle_gone_branches(cfg: Config) -> None:
    """Handle branches with gone remotes."""
    gone_branches = get_gone_branches()
    if not gone_branches:
        console.print("[blue]No branches with gone remotes found[/blue]")
        return

    protected_branches = filter_protected_branches(
        gone_branches,
        cfg.protected_branches,
    )
    if not protected_branches:
        console.print("[blue]All gone branches are protected[/blue]")
        return

    console.print("[yellow]Found branches with gone remotes:[/yellow]")
    for branch in protected_branches:
        console.print(f"  {branch}")

    delete_branches(
        protected_branches,
        dry_run=cfg.dry_run_by_default,
        interactive=cfg.interactive,
        force=True,
    )


def handle_merged_branches(cfg: Config) -> None:
    """Handle merged local branches."""
    merged_branches = get_merged_branches()
    if not merged_branches:
        console.print("[blue]No merged branches found[/blue]")
        return

    protected_branches = filter_protected_branches(
        merged_branches,
        cfg.protected_branches,
    )
    if not protected_branches:
        console.print("[blue]All merged branches are protected[/blue]")
        return

    console.print("[yellow]Found merged branches:[/yellow]")
    for branch in protected_branches:
        console.print(f"  {branch}")

    try:
        delete_branches(
            protected_branches,
            dry_run=cfg.dry_run_by_default,
            interactive=cfg.interactive,
        )
    except GitError as e:
        console.print(f"[red]Error deleting branches: {e}[/red]")
        raise


def handle_merged_remote_branches(cfg: Config) -> None:
    """Handle merged remote branches."""
    merged_branches = get_merged_remote_branches()
    if not merged_branches:
        console.print("[blue]No merged remote branches found[/blue]")
        return

    protected_branches = filter_protected_branches(
        merged_branches,
        cfg.protected_branches,
    )
    if not protected_branches:
        console.print("[blue]All merged remote branches are protected[/blue]")
        return

    console.print("[yellow]Found merged remote branches:[/yellow]")
    for branch in protected_branches:
        console.print(f"  {branch}")

    try:
        delete_remote_branches(
            protected_branches,
            dry_run=cfg.dry_run_by_default,
            interactive=cfg.interactive,
        )
    except GitError as e:
        console.print(f"[red]Error deleting remote branches: {e}[/red]")
        raise


def _confirm_bulk_deletion(branches: list[str]) -> bool:
    """Ask for confirmation before deleting multiple branches."""
    branch_list = "\n".join(f"  - {branch}" for branch in branches)
    return Confirm.ask(
        f"Delete the following branches?\n{branch_list}",
        default=False,
    )


def _delete_single_branch(
    branch: str,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Delete a single branch after confirmation.

    Parameters
    ----------
    branch : str
        Branch to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.
    force : bool, optional
        Whether to force delete the branch, by default False.

    Returns
    -------
    bool
        True if the branch was deleted successfully or skipped, False otherwise.

    """
    if not Confirm.ask(f"Delete branch {branch}?", default=False):
        console.print(f"Skipping branch {branch}")
        return True

    if dry_run:
        console.print(f"Would delete branch {branch}")
        return True

    try:
        git.delete_branch(branch, force=force)
        console.print(f"Deleted branch {branch}")
        return True
    except git.GitError as e:
        console.print(f"Error deleting branch {branch}: {e}", style="red")
        return False


def _delete_branches_non_interactive(
    branches: list[str],
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Delete branches without asking for confirmation.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.
    force : bool, optional
        Whether to force delete branches, by default False.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if dry_run:
        for branch in branches:
            console.print(f"Would delete branch {branch}")
        return True

    for branch in branches:
        try:
            git.delete_branch(branch, force=force)
            console.print(f"Deleted branch {branch}")
        except git.GitError as e:
            console.print(f"Error deleting branch {branch}: {e}", style="red")
            return False
    return True


def _delete_branches_interactive(
    branches: list[str],
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Delete branches with interactive confirmation.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.
    force : bool, optional
        Whether to force delete branches, by default False.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if len(branches) > 1 and _confirm_bulk_deletion(branches):
        for branch in branches:
            if not _delete_single_branch(branch, dry_run, force):
                return False
        return True

    for branch in branches:
        if not _delete_single_branch(branch, dry_run, force):
            return False

    return True


def delete_branches(
    branches: list[str],
    dry_run: bool = False,
    interactive: bool = True,
    force: bool = False,
) -> bool:
    """Delete local branches.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.
    interactive : bool, optional
        Whether to ask for confirmation before deleting branches, by default True.
    force : bool, optional
        Whether to force delete branches, by default False.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if not branches:
        return True

    if not interactive:
        return _delete_branches_non_interactive(branches, dry_run, force)
    return _delete_branches_interactive(branches, dry_run, force)


def _delete_remote_branches_non_interactive(
    branches: list[str],
    dry_run: bool = False,
) -> bool:
    """Delete remote branches without asking for confirmation.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if dry_run:
        for branch in branches:
            console.print(f"Would delete remote branch {branch}")
        return True

    for branch in branches:
        try:
            delete_remote_branch(branch)
            console.print(f"Deleted remote branch {branch}")
        except GitError as e:
            console.print(
                f"Error deleting remote branch {branch}: {e}",
                style="red",
            )
            return False
    return True


def _delete_remote_branches_interactive(
    branches: list[str],
    dry_run: bool = False,
) -> bool:
    """Delete remote branches with interactive confirmation.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if len(branches) > 1 and _confirm_bulk_deletion(branches):
        for branch in branches:
            if not _delete_single_branch(branch, dry_run):
                return False
        return True

    for branch in branches:
        if not _delete_single_branch(branch, dry_run):
            return False

    return True


def delete_remote_branches(
    branches: list[str],
    dry_run: bool = False,
    interactive: bool = True,
) -> bool:
    """Delete remote branches.

    Parameters
    ----------
    branches : list[str]
        List of branches to delete.
    dry_run : bool, optional
        Whether to show what would be done without making changes, by default False.
    interactive : bool, optional
        Whether to ask for confirmation before deleting branches, by default True.

    Returns
    -------
    bool
        True if all branches were deleted successfully, False otherwise.

    """
    if not branches:
        return True

    if not interactive:
        return _delete_remote_branches_non_interactive(branches, dry_run)
    return _delete_remote_branches_interactive(branches, dry_run)


def optimize_repository(skip_gc: bool = False) -> None:
    """Run git gc to optimize the repository."""
    if skip_gc:
        console.print("[blue]Skipping repository optimization[/blue]")
        return

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]Optimizing repository...[/blue]"),
            transient=True,
        ) as progress:
            progress.add_task("optimize", total=None)
            optimize_repo()
        console.print("[green]Repository optimized[/green]")
    except GitError as e:
        console.print(f"[red]Error optimizing repository: {e}[/red]")


def update_config_from_options(
    cfg: Config,
    dry_run: bool | None,
    interactive: bool | None,
    no_gc: bool | None,
    protect: list[str] | None,
) -> None:
    """Update config with command line options."""
    if dry_run is not None:
        cfg.dry_run_by_default = dry_run

    if interactive is not None:
        cfg.interactive = interactive
    else:
        cfg.interactive = True  # Default to interactive mode if not specified

    if no_gc is not None:
        cfg.skip_gc = no_gc

    if protect:
        cfg.protected_branches.extend(protect)
        # Remove duplicates while preserving order
        cfg.protected_branches = list(dict.fromkeys(cfg.protected_branches))


def parse_protect_option(value: str) -> list[str]:
    """Parse the protect option value."""
    if not value:
        return []
    return [branch.strip() for branch in value.split(",")]


def _handle_gone_branches(
    config: Config,
    dry_run: bool,
    interactive: bool,
) -> None:
    """Handle branches with gone remotes.

    Parameters
    ----------
    config : Config
        Configuration object.
    dry_run : bool
        Whether to show what would be done without making changes.
    interactive : bool
        Whether to ask for confirmation before deleting branches.

    """
    gone_branches = git.get_gone_branches()
    if not gone_branches:
        console.print("No branches with gone remotes found")
        return

    protected = set(config.protected_branches)
    gone_branches = [b for b in gone_branches if b not in protected]
    if not gone_branches:
        console.print("All gone branches are protected")
        return

    console.print("\nBranches with gone remotes:")
    for branch in gone_branches:
        console.print(f"  - {branch}")

    if not delete_branches(gone_branches, dry_run, interactive):
        raise typer.Exit(code=1)


def _handle_merged_branches(
    config: Config,
    dry_run: bool,
    interactive: bool,
) -> None:
    """Handle merged branches.

    Parameters
    ----------
    config : Config
        Configuration object.
    dry_run : bool
        Whether to show what would be done without making changes.
    interactive : bool
        Whether to ask for confirmation before deleting branches.

    """
    merged_branches = git.get_merged_branches()
    if not merged_branches:
        console.print("No merged branches found")
        return

    protected = set(config.protected_branches)
    merged_branches = [b for b in merged_branches if b not in protected]
    if not merged_branches:
        console.print("All merged branches are protected")
        return

    console.print("\nMerged branches:")
    for branch in merged_branches:
        console.print(f"  - {branch}")

    if not delete_branches(merged_branches, dry_run, interactive, force=True):
        raise typer.Exit(code=1)


@app.command()
def main(
    no_interactive: bool = NO_INTERACTIVE_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    no_gc: bool = NO_GC_OPTION,
    protect: list[str] | None = PROTECT_OPTION,
    config_path: str = CONFIG_PATH_OPTION,
) -> None:
    """Clean up gone and merged branches."""
    try:
        config = load_config(config_path)
    except ConfigError as e:
        console.print(f"Error loading config: {e}", style="red")
        raise typer.Exit(code=1) from e

    if not git.is_git_repo():
        console.print("Not in a git repository", style="red")
        raise typer.Exit(code=1)

    interactive = not no_interactive
    if dry_run is None:
        dry_run = config.dry_run_by_default
    if no_gc is None:
        skip_gc = config.skip_gc
    else:
        skip_gc = no_gc

    if protect:
        config.protected_branches.extend(protect)

    try:
        _handle_gone_branches(config, dry_run, interactive)
        _handle_merged_branches(config, dry_run, interactive)

        if not skip_gc:
            git.optimize_repo()

    except git.GitError as e:
        console.print(f"Git error: {e}", style="red")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
