"""CLI interface for arborist."""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from arborist.config import Config, load_config
from arborist.git import (
    GitError,
    delete_branch,
    delete_remote_branch,
    fetch_and_prune,
    filter_protected_branches,
    get_gone_branches,
    get_merged_branches,
    get_merged_remote_branches,
    is_git_repo,
    optimize_repo,
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
    console.print("\n🔍 [blue]Checking for branches with gone remotes...[/blue]")
    gone_branches = get_gone_branches()
    gone_branches = filter_protected_branches(gone_branches, cfg.protected_branches)

    if not gone_branches:
        console.print("[green]No branches with gone remotes found.[/green]")
        return

    console.print(
        f"[yellow]Found {len(gone_branches)} branches with gone remotes:[/yellow]",
    )
    for branch in gone_branches:
        console.print(f"[yellow]  {branch}[/yellow]")

    delete_branches(
        gone_branches,
        dry_run=cfg.dry_run_by_default,
        interactive=cfg.interactive,
        force=True,
    )


def handle_merged_branches(cfg: Config) -> None:
    """Handle merged branches."""
    console.print("\n🧹 [blue]Checking for merged branches...[/blue]")
    merged_branches = get_merged_branches()
    merged_branches = filter_protected_branches(
        merged_branches,
        cfg.protected_branches,
    )

    if not merged_branches:
        console.print("[green]No merged branches found.[/green]")
        return

    console.print(f"[yellow]Found {len(merged_branches)} merged branches:[/yellow]")
    for branch in merged_branches:
        console.print(f"[yellow]  {branch}[/yellow]")

    delete_branches(
        merged_branches,
        dry_run=cfg.dry_run_by_default,
        interactive=cfg.interactive,
    )


def handle_merged_remote_branches(cfg: Config) -> None:
    """Handle merged remote branches."""
    console.print("\n🌐 [blue]Checking for merged remote branches...[/blue]")
    merged_remotes = get_merged_remote_branches()
    merged_remotes = filter_protected_branches(
        merged_remotes,
        cfg.protected_branches,
    )

    if not merged_remotes:
        console.print("[green]No merged remote branches found.[/green]")
        return

    console.print(
        f"[yellow]Found {len(merged_remotes)} merged remote branches:[/yellow]",
    )
    for branch in merged_remotes:
        console.print(f"[yellow]  {branch}[/yellow]")

    delete_remote_branches(
        merged_remotes,
        dry_run=cfg.dry_run_by_default,
        interactive=cfg.interactive,
    )


def _confirm_bulk_deletion(
    branches: list[str], dry_run: bool, is_remote: bool = False
) -> bool:
    """Ask for confirmation before bulk deletion.

    Args:
    ----
        branches: List of branch names to delete
        dry_run: Whether this is a dry run
        is_remote: Whether these are remote branches

    Returns:
    -------
        bool: Whether to proceed with deletion

    """
    branch_type = "remote branches" if is_remote else "branches"
    console.print(f"\n[yellow]The following {branch_type} will be deleted:[/yellow]")
    for branch in branches:
        console.print(f"  [yellow]{branch}[/yellow]")

    if dry_run:
        console.print("[blue]Dry run mode - no changes will be made.[/blue]")
        return False

    prompt = f"\n[yellow]Do you want to proceed with {branch_type} deletion?[/yellow]"
    if not Confirm.ask(prompt, default=False):
        console.print(f"[blue]Skipping {branch_type} deletion.[/blue]")
        return False

    return True


def _delete_single_branch(
    branch: str,
    dry_run: bool,
    interactive: bool,
    force: bool = False,
    is_remote: bool = False,
) -> None:
    """Delete a single branch.

    Args:
    ----
        branch: Name of the branch to delete
        dry_run: Whether this is a dry run
        interactive: Whether to ask for confirmation
        force: Whether to force delete the branch
        is_remote: Whether this is a remote branch

    """
    branch_type = "remote" if is_remote else ""
    try:
        if interactive:
            prompt = (
                f"Delete {branch_type} branch {branch}?"
                if branch_type
                else f"Delete branch {branch}?"
            )
            if not Confirm.ask(prompt, default=False):
                console.print(f"[blue]Skipping {branch_type} branch {branch}[/blue]")
                return

        if dry_run:
            console.print(f"[blue]Would delete {branch_type} branch {branch}[/blue]")
            return

        if is_remote:
            delete_remote_branch(branch)
        else:
            delete_branch(branch, force=force)
        console.print(f"[green]Deleted {branch_type} branch {branch}[/green]")

    except GitError as e:
        error_msg = f"[red]Error deleting {branch}: {e!s}[/red]"
        console.print(error_msg)


def delete_branches(
    branches: list[str],
    dry_run: bool = False,
    interactive: bool = True,
    force: bool = False,
) -> None:
    """Delete the given branches.

    Args:
    ----
        branches: List of branch names to delete
        dry_run: Whether to only show what would be deleted (defaults to False)
        interactive: Whether to ask for confirmation before deleting (defaults to True)
        force: Whether to force delete branches (-D instead of -d)

    """
    if not branches:
        return

    if interactive and not _confirm_bulk_deletion(branches, dry_run):
        return

    for branch in branches:
        _delete_single_branch(branch, dry_run, interactive, force)


def delete_remote_branches(
    branches: list[str],
    dry_run: bool = False,
    interactive: bool = True,
) -> None:
    """Delete the given remote branches.

    Args:
    ----
        branches: List of remote branch names to delete
        dry_run: Whether to only show what would be deleted (defaults to False)
        interactive: Whether to ask for confirmation before deleting (defaults to True)

    """
    if not branches:
        return

    if interactive and not _confirm_bulk_deletion(branches, dry_run, is_remote=True):
        return

    for branch in branches:
        _delete_single_branch(branch, dry_run, interactive, is_remote=True)


def optimize_repository(cfg: Config) -> None:
    """Optimize the git repository."""
    if cfg.skip_gc or cfg.dry_run_by_default:
        return

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]{task.description}[/blue]"),
            console=console,
        ) as progress:
            task_id = progress.add_task("⚡ Optimizing repository...", total=None)
            optimize_repo(
                progress_callback=lambda msg: progress.update(
                    task_id,
                    description=f"⚡ {msg}",
                ),
            )
        console.print("[green]Repository optimized successfully.[/green]")
    except GitError as e:
        console.print(f"[red]Error optimizing repository: {e!s}[/red]")


def update_config_from_options(
    cfg: Config,
    dry_run: bool | None,
    interactive: bool | None,
    no_gc: bool | None,
    protect: list[str] | None,
) -> None:
    """Update configuration with CLI options."""
    if dry_run is not None:
        cfg.dry_run_by_default = dry_run
    if interactive is not None:
        cfg.interactive = interactive
    if no_gc is not None:
        cfg.skip_gc = no_gc
    if protect:
        cfg.protected_branches.extend(protect)


# CLI option definitions
dry_run_option = typer.Option(
    False,
    "--dry-run",
    "-d",
    help="Show what would be deleted without actually deleting",
)
no_interactive_option = typer.Option(
    False,
    "--no-interactive",
    "-n",
    help="Don't ask for confirmation before deleting branches",
)
no_gc_option = typer.Option(
    False,
    "--no-gc",
    help="Skip garbage collection",
)


def parse_protect_option(value: str) -> list[str]:
    """Parse comma-separated protect option into list of branch names."""
    if not value:
        return []
    return [branch.strip() for branch in value.split(",")]


protect_option = typer.Option(
    "",
    "--protect",
    "-p",
    help="Additional protected branches (comma-separated)",
    callback=parse_protect_option,
)


@app.command()
def main(
    dry_run: bool = dry_run_option,
    no_interactive: bool = no_interactive_option,
    no_gc: bool = no_gc_option,
    protect: str = protect_option,
) -> None:
    """Clean up git branches that are gone or merged."""
    # Validate git repository
    validate_git_repo()

    # Load and update configuration
    cfg = load_config()
    update_config_from_options(cfg, dry_run, not no_interactive, no_gc, protect)

    # Start cleanup
    console.print("🧹 [blue]Starting git cleanup...[/blue]")

    if cfg.dry_run_by_default:
        console.print("[yellow]DRY RUN: No changes will be made[/yellow]")

    # Update repository state
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]{task.description}[/blue]"),
            console=console,
        ) as progress:
            task_id = progress.add_task("🔄 Updating repository state...", total=None)
            fetch_and_prune(
                progress_callback=lambda msg: progress.update(
                    task_id,
                    description=f"🔄 {msg}",
                ),
            )
    except GitError as err:
        console.print(f"[red]Error updating repository state: {err!s}[/red]")
        raise typer.Exit(code=1) from err

    # Process branches
    handle_gone_branches(cfg)
    handle_merged_branches(cfg)
    handle_merged_remote_branches(cfg)

    # Optimize repository
    try:
        optimize_repository(cfg)
    except GitError as err:
        console.print(f"[red]Error optimizing repository: {err!s}[/red]")
        raise typer.Exit(code=1) from err

    console.print("\n✨ [green]Cleanup complete![/green]")


if __name__ == "__main__":
    app()
