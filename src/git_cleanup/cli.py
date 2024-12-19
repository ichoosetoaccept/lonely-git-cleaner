"""CLI interface for git-cleanup."""


import typer
from rich.console import Console
from rich.prompt import Confirm

from . import config, git

app = typer.Typer(
    help="Clean up git branches that are gone or merged.",
    add_completion=False,
)
console = Console()


def validate_git_repo() -> None:
    """Validate we're in a git repository."""
    if not git.is_git_repo():
        console.print("[red]Error: Not a git repository[/red]")
        raise typer.Exit(1)


def handle_gone_branches(cfg: config.Config) -> None:
    """Handle branches with gone remotes."""
    console.print("\n🔍 [blue]Checking for branches with gone remotes...[/blue]")
    gone_branches = git.get_gone_branches()
    gone_branches = git.filter_protected_branches(gone_branches, cfg.protected_branches)

    if not gone_branches:
        console.print("[green]No branches with gone remotes found.[/green]")
        return

    console.print(
        f"[yellow]Found {len(gone_branches)} branches with gone remotes:[/yellow]",
    )
    for branch in gone_branches:
        console.print(f"[yellow]  {branch}[/yellow]")

    if not cfg.dry_run_by_default:
        delete_branches(gone_branches, cfg.interactive, force=True)


def handle_merged_branches(cfg: config.Config) -> None:
    """Handle merged branches."""
    console.print("\n🧹 [blue]Checking for merged branches...[/blue]")
    merged_branches = git.get_merged_branches()
    merged_branches = git.filter_protected_branches(
        merged_branches,
        cfg.protected_branches,
    )

    if not merged_branches:
        console.print("[green]No merged branches found.[/green]")
        return

    console.print(f"[yellow]Found {len(merged_branches)} merged branches:[/yellow]")
    for branch in merged_branches:
        console.print(f"[yellow]  {branch}[/yellow]")

    if not cfg.dry_run_by_default:
        delete_branches(merged_branches, cfg.interactive)


def delete_branches(
    branches: list[str],
    interactive: bool,
    force: bool = False,
) -> None:
    """Delete the given branches."""
    for branch in branches:
        if interactive:
            if not Confirm.ask(f"Delete branch {branch}?", default=False):
                continue
        try:
            git.delete_branch(branch, force=force)
            console.print(f"[green]Deleted branch {branch}[/green]")
        except git.GitError as e:
            console.print(f"[red]Error deleting {branch}: {e!s}[/red]")


def optimize_repository(cfg: config.Config) -> None:
    """Optimize the git repository."""
    if cfg.skip_gc or cfg.dry_run_by_default:
        return

    console.print("\n⚡ [blue]Optimizing repository...[/blue]")
    try:
        git.optimize_repo()
        console.print("[green]Repository optimized successfully.[/green]")
    except git.GitError as e:
        console.print(f"[red]Error optimizing repository: {e!s}[/red]")


def update_config_from_options(
    cfg: config.Config,
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
interactive_option = typer.Option(
    False,
    "--interactive",
    "-i",
    help="Ask before each deletion",
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
    interactive: bool = interactive_option,
    no_gc: bool = no_gc_option,
    protect: str = protect_option,
) -> None:
    """Clean up git branches that are gone or merged."""
    # Validate git repository
    validate_git_repo()

    # Load and update configuration
    cfg = config.load_config()
    update_config_from_options(cfg, dry_run, interactive, no_gc, protect)

    # Start cleanup
    console.print("🧹 [blue]Starting git cleanup...[/blue]")

    if cfg.dry_run_by_default:
        console.print("[yellow]DRY RUN: No changes will be made[/yellow]")

    # Update repository state
    console.print("\n🔄 [blue]Fetching and pruning remotes...[/blue]")
    if not cfg.dry_run_by_default:
        git.fetch_and_prune()

    # Process branches
    handle_gone_branches(cfg)
    handle_merged_branches(cfg)

    # Optimize repository
    optimize_repository(cfg)

    console.print("\n✨ [green]Cleanup complete![/green]")


if __name__ == "__main__":
    app()
