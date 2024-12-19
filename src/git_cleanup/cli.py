"""CLI interface for git-cleanup."""

from typing import List, Optional

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


@app.command()
def main(
    dry_run: bool = typer.Option(
        None,
        "--dry-run",
        "-d",
        help="Show what would be deleted without actually deleting",
    ),
    interactive: bool = typer.Option(
        None,
        "--interactive",
        "-i",
        help="Ask before each deletion",
    ),
    no_gc: bool = typer.Option(
        None,
        "--no-gc",
        help="Skip garbage collection",
    ),
    protect: Optional[List[str]] = typer.Option(
        None,
        "--protect",
        "-p",
        help="Additional protected branches (comma-separated)",
    ),
) -> None:
    """Clean up git branches that are gone or merged."""
    # Validate git repository
    validate_git_repo()

    # Load configuration
    cfg = config.load_config()

    # Override config with CLI options if provided
    if dry_run is not None:
        cfg.dry_run_by_default = dry_run
    if interactive is not None:
        cfg.interactive = interactive
    if no_gc is not None:
        cfg.skip_gc = no_gc
    if protect:
        cfg.protected_branches.extend(protect)

    # Start cleanup
    console.print("🧹 [blue]Starting git cleanup...[/blue]")

    if cfg.dry_run_by_default:
        console.print("[yellow]DRY RUN: No changes will be made[/yellow]")

    # Update repository state
    console.print("\n🔄 [blue]Fetching and pruning remotes...[/blue]")
    if not cfg.dry_run_by_default:
        git.fetch_and_prune()

    # Handle gone branches
    console.print("\n🔍 [blue]Checking for branches with gone remotes...[/blue]")
    gone_branches = git.get_gone_branches()
    gone_branches = git.filter_protected_branches(gone_branches, cfg.protected_branches)

    if not gone_branches:
        console.print("[green]No branches with gone remotes found.[/green]")
    else:
        console.print(f"[yellow]Found {len(gone_branches)} branches with gone remotes:[/yellow]")
        for branch in gone_branches:
            console.print(f"[yellow]  {branch}[/yellow]")

        if not cfg.dry_run_by_default:
            for branch in gone_branches:
                if cfg.interactive:
                    if not Confirm.ask(f"Delete branch {branch}?", default=False):
                        continue
                try:
                    git.delete_branch(branch, force=True)
                    console.print(f"[green]Deleted branch {branch}[/green]")
                except git.GitError as e:
                    console.print(f"[red]Error deleting {branch}: {str(e)}[/red]")

    # Handle merged branches
    console.print("\n🧹 [blue]Checking for merged branches...[/blue]")
    merged_branches = git.get_merged_branches()
    merged_branches = git.filter_protected_branches(merged_branches, cfg.protected_branches)

    if not merged_branches:
        console.print("[green]No merged branches found.[/green]")
    else:
        console.print(f"[yellow]Found {len(merged_branches)} merged branches:[/yellow]")
        for branch in merged_branches:
            console.print(f"[yellow]  {branch}[/yellow]")

        if not cfg.dry_run_by_default:
            for branch in merged_branches:
                if cfg.interactive:
                    if not Confirm.ask(f"Delete branch {branch}?", default=False):
                        continue
                try:
                    git.delete_branch(branch)
                    console.print(f"[green]Deleted branch {branch}[/green]")
                except git.GitError as e:
                    console.print(f"[red]Error deleting {branch}: {str(e)}[/red]")

    # Optimize repository
    if not cfg.skip_gc and not cfg.dry_run_by_default:
        console.print("\n⚡ [blue]Optimizing repository...[/blue]")
        try:
            git.optimize_repo()
            console.print("[green]Repository optimized successfully.[/green]")
        except git.GitError as e:
            console.print(f"[red]Error optimizing repository: {str(e)}[/red]")

    console.print("\n✨ [green]Cleanup complete![/green]")


if __name__ == "__main__":
    app()
