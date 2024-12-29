"""Test CLI functionality."""

from io import StringIO
from unittest.mock import call, patch

import pytest
from arborist import cli, git
from arborist.config import Config
from arborist.git import GitError
from typer.testing import CliRunner

# Constants for test assertions
BULK_AND_TWO_BRANCHES = 3  # One bulk confirmation + two branch confirmations
TWO_BRANCHES = 2  # Two branch operations
BULK_AND_ONE_BRANCH = 2  # One bulk confirmation + one branch confirmation


def raise_(ex):
    """Raise the given exception."""
    raise ex


runner = CliRunner()


@pytest.fixture
def mock_config(mocker):
    """Mock config loading."""
    config = Config(
        protected_branches=["main"],
        dry_run_by_default=False,
        interactive=True,
        skip_gc=False,
    )
    mock = mocker.patch("arborist.cli.load_config")
    mock.return_value = config
    return mock


@pytest.fixture
def mock_git(mocker):
    """Mock git functions."""
    mocker.patch("arborist.git.is_git_repo", return_value=True)
    mocker.patch("arborist.git.get_gone_branches", return_value=[])
    mocker.patch("arborist.git.get_merged_branches", return_value=[])
    mocker.patch("arborist.git.get_merged_remote_branches", return_value=[])
    mocker.patch("arborist.git.delete_branch")
    mocker.patch("arborist.git.delete_remote_branch")
    mocker.patch("arborist.git.optimize_repo")
    return {}


def test_validate_git_repo():
    """Test git repository validation."""
    with (
        patch("arborist.cli.is_git_repo", return_value=False),
        patch("rich.console.Console.print") as mock_print,
    ):
        result = runner.invoke(cli.app, catch_exceptions=False)
        print(f"Exit code: {result.exit_code}")
        print(f"Stdout: {result.stdout}")
        print(f"Mock print calls: {mock_print.mock_calls}")
        assert result.exit_code == 1
        mock_print.assert_any_call("[red]Error: Not a git repository[/red]")


def test_main_not_git_repo(mock_config):
    """Test handling non-git repository."""
    with patch("arborist.cli.is_git_repo", return_value=False):
        result = runner.invoke(cli.app, catch_exceptions=False)
        assert result.exit_code == 1
        assert "Error: Not a git repository" in result.stdout


def test_main_no_branches(mock_config, mock_git):
    """Test when no branches to clean."""
    with patch("arborist.git.is_git_repo", return_value=True):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "No branches with gone remotes found" in result.stdout
        assert "No merged branches found" in result.stdout
        assert "No merged remote branches found" in result.stdout


def test_main_with_gone_branches(mock_config):
    """Test cleaning gone branches."""
    mock_config.return_value = Config(
        protected_branches=["main"],
        dry_run_by_default=False,
        interactive=False,
        skip_gc=False,
    )
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: ["feature/123"],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            delete_branch=lambda *args, **kwargs: None,
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        result = runner.invoke(cli.app, ["--no-interactive"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Found 1 branches with gone remotes" in result.stdout
        assert "feature/123" in result.stdout


def test_main_with_merged_branches(mock_config):
    """Test cleaning merged branches."""
    mock_config.return_value = Config(
        protected_branches=["main"],
        dry_run_by_default=False,
        interactive=False,
        skip_gc=False,
    )
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: [],
            get_merged_branches=lambda: ["feature/456", "hotfix/789"],
            get_merged_remote_branches=lambda: [],
            delete_branch=lambda *args, **kwargs: None,
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        result = runner.invoke(cli.app, ["--no-interactive"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Found 2 merged branches" in result.stdout
        assert "feature/456" in result.stdout
        assert "hotfix/789" in result.stdout


def test_main_dry_run(mock_config, mock_git):
    """Test dry run mode."""
    result = runner.invoke(cli.app, ["--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN: No changes will be made" in result.stdout


def test_main_interactive_mode(mock_config):
    """Test interactive mode."""
    mock_config.return_value = Config(
        protected_branches=["main"],
        dry_run_by_default=False,
        interactive=True,
        skip_gc=False,
    )
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: ["feature/123"],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            delete_branch=lambda *args, **kwargs: None,
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", side_effect=[True, True]),
    ):
        result = runner.invoke(cli.app, catch_exceptions=False)
        assert result.exit_code == 0
        assert "feature/123" in result.stdout


def test_fetch_prune_progress(mock_config):
    """Test progress bar during fetch and prune operations."""
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: [],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("arborist.cli.fetch_and_prune") as mock_fetch,
    ):

        def progress_callback(message):
            assert "Fetching" in message or "Pruning" in message

        mock_fetch.side_effect = lambda progress_callback=None: (
            progress_callback("Fetching and pruning...") if progress_callback else None
        )

        result = runner.invoke(cli.app, catch_exceptions=False)
        assert result.exit_code == 0
        assert mock_fetch.called


def test_optimize_progress(mock_config):
    """Test progress bar during repository optimization."""
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: [],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            fetch_and_prune=lambda progress_callback=None: None,
        ),
        patch("arborist.cli.optimize_repo") as mock_optimize,
    ):

        def progress_callback(message):
            assert "Optimizing" in message or "Repository optimization" in message

        mock_optimize.side_effect = lambda progress_callback=None: (
            progress_callback("Optimizing repository...") if progress_callback else None
        )

        result = runner.invoke(cli.app, catch_exceptions=False)
        assert result.exit_code == 0
        assert mock_optimize.called


def test_main_no_gc(mock_config, mock_git):
    """Test skipping repository optimization."""
    result = runner.invoke(cli.app, ["--no-gc"])
    assert result.exit_code == 0
    assert not git.optimize_repo.called


def test_main_protect_branches(mock_config):
    """Test protecting additional branches."""
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: ["develop", "feature/123", "staging"],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            filter_protected_branches=git.filter_protected_branches,
            delete_branch=lambda *args, **kwargs: None,
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        result = runner.invoke(
            cli.app,
            ["--protect", "develop,staging"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "Found 1 branches with gone remotes" in result.stdout
        assert "feature/123" in result.stdout
        assert "develop" not in result.stdout
        assert "staging" not in result.stdout


def test_main_error_handling(mock_config):
    """Test handling git errors."""
    with (
        patch.multiple(
            "arborist.cli",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: ["feature/123"],
            get_merged_branches=lambda: [],
            get_merged_remote_branches=lambda: [],
            delete_branch=lambda *args, **kwargs: raise_(GitError("test error")),
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        result = runner.invoke(cli.app, catch_exceptions=False)
        assert result.exit_code == 0  # Should not exit with error
        assert "Error deleting feature/123: test error" in result.stdout


def test_delete_branches_interactive_individual_choices(mock_config):
    """Test mixed acceptance/rejection of individual branches."""
    stdout = StringIO()
    with (
        patch(
            "rich.prompt.Confirm.ask",
            side_effect=[True, True, False],
        ) as mock_confirm,
        patch("arborist.cli.delete_branch") as mock_delete,
        patch("sys.stdout", stdout),
    ):
        branches = ["feature/123", "feature/456"]
        cli.delete_branches(branches, dry_run=False, interactive=True)

        # First True is for bulk confirmation
        # Second True is for first branch
        # False is for second branch
        assert mock_confirm.call_count == BULK_AND_TWO_BRANCHES
        mock_delete.assert_called_once_with("feature/123", force=False)
        output = stdout.getvalue()
        assert "Skipping branch feature/456" in output.replace("  ", " ")


def test_delete_branches_non_interactive(mock_config):
    """Test non-interactive branch deletion."""
    with patch("rich.prompt.Confirm.ask"):
        with patch("arborist.cli.delete_branch") as mock_delete:
            branches = ["feature/123", "feature/456"]
            cli.delete_branches(branches, dry_run=False, interactive=False)

            assert mock_delete.call_count == TWO_BRANCHES
            mock_delete.assert_has_calls(
                [
                    call("feature/123", force=False),
                    call("feature/456", force=False),
                ],
            )


def test_delete_remote_branches_none():
    """Test when no remote branches to delete."""
    cli.delete_remote_branches([], dry_run=False, interactive=False)


def test_delete_remote_branches_non_interactive(mocker):
    """Test deleting remote branches in non-interactive mode."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask")
    mock_delete = mocker.patch("arborist.cli.delete_remote_branch")

    branches = ["feature/123", "feature/456"]
    cli.delete_remote_branches(branches, dry_run=False, interactive=False)

    assert not mock_confirm.called
    assert mock_delete.call_count == TWO_BRANCHES
    mock_delete.assert_has_calls(
        [call("feature/123"), call("feature/456")],
    )


def test_delete_remote_branches_interactive_confirm(mocker):
    """Test deleting remote branches with interactive confirmation."""
    mock_confirm = mocker.patch(
        "rich.prompt.Confirm.ask",
        side_effect=[True, True, True],
    )
    mock_delete = mocker.patch("arborist.cli.delete_remote_branch")
    mock_console = mocker.patch("rich.console.Console.print")

    branches = ["feature/123", "feature/456"]
    cli.delete_remote_branches(branches, dry_run=False, interactive=True)

    # First True is for bulk confirmation
    # Second and third True are for individual branches
    assert mock_confirm.call_count == BULK_AND_TWO_BRANCHES
    assert mock_delete.call_count == TWO_BRANCHES
    mock_delete.assert_has_calls(
        [call("feature/123"), call("feature/456")],
    )
    mock_console.assert_any_call(
        "[green]Deleted remote branch feature/123[/green]",
    )
    mock_console.assert_any_call(
        "[green]Deleted remote branch feature/456[/green]",
    )


def test_delete_remote_branches_interactive_reject(mocker):
    """Test rejecting remote branch deletion in interactive mode."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=False)
    mock_delete = mocker.patch("arborist.git.delete_remote_branch")

    branches = ["feature/123", "feature/456"]
    cli.delete_remote_branches(branches, dry_run=False, interactive=True)

    # Only called once for bulk confirmation, rejected
    assert mock_confirm.call_count == 1
    assert not mock_delete.called


def test_delete_remote_branches_error_handling(mocker):
    """Test error handling during remote branch deletion."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", side_effect=[True, True])
    mock_delete = mocker.patch(
        "arborist.cli.delete_remote_branch",
        side_effect=GitError("Remote branch deletion failed"),
    )

    branches = ["feature/123"]
    cli.delete_remote_branches(branches, dry_run=False, interactive=True)

    # Called for bulk confirmation and individual branch
    assert mock_confirm.call_count == BULK_AND_ONE_BRANCH
    assert mock_delete.called
    assert mock_delete.call_count == 1


def test_delete_branches_error_handling(mocker):
    """Test error handling during branch deletion."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", side_effect=[True, True])
    mock_delete = mocker.patch(
        "arborist.cli.delete_branch",
        side_effect=GitError("Branch deletion failed"),
    )
    mock_console = mocker.patch("rich.console.Console.print")

    branches = ["feature/123"]
    cli.delete_branches(branches, dry_run=False, interactive=True)

    # Called for bulk confirmation and individual branch
    assert mock_confirm.call_count == BULK_AND_ONE_BRANCH
    assert mock_delete.called
    assert mock_delete.call_count == 1
    mock_console.assert_any_call(
        "[red]Error deleting feature/123: Branch deletion failed[/red]",
    )


def test_main_with_all_options(mock_config):
    """Test main function with all options enabled."""
    with (
        patch.multiple(
            "arborist.git",
            is_git_repo=lambda: True,
            get_gone_branches=lambda: ["feature/123"],
            get_merged_branches=lambda: ["feature/456"],
            get_merged_remote_branches=lambda: ["feature/789"],
            delete_branch=lambda *args, **kwargs: None,
            delete_remote_branch=lambda *args, **kwargs: None,
            fetch_and_prune=lambda progress_callback=None: None,
            optimize_repo=lambda progress_callback=None: None,
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        result = runner.invoke(
            cli.app,
            [
                "--dry-run",
                "--no-interactive",
                "--no-gc",
                "--protect",
                "develop,staging",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "DRY RUN: No changes will be made" in result.stdout


def test_main_with_optimize_error(mock_config):
    """Test main function when optimization fails."""
    with patch.multiple(
        "arborist.cli",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
        get_merged_remote_branches=lambda: [],
        fetch_and_prune=lambda progress_callback=None: None,
        optimize_repo=lambda progress_callback=None: raise_(GitError("GC failed")),
    ):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0  # Should not exit with error
        assert "Error optimizing repository: GC failed" in result.stdout


def test_delete_branches_with_error_and_continue(mocker):
    """Test branch deletion with error on one branch but continuing."""
    mock_confirm = mocker.patch(
        "rich.prompt.Confirm.ask",
        side_effect=[True, True, True],
    )
    mock_delete = mocker.patch(
        "arborist.cli.delete_branch",
        side_effect=[GitError("First failed"), None],
    )

    branches = ["feature/123", "feature/456"]
    cli.delete_branches(branches, dry_run=False, interactive=True)

    # Called for bulk confirmation and both branches
    assert mock_confirm.call_count == BULK_AND_TWO_BRANCHES
    assert mock_delete.call_count == TWO_BRANCHES
    mock_delete.assert_has_calls(
        [call("feature/123", force=False), call("feature/456", force=False)],
    )


def test_main_with_fetch_error(mock_config):
    """Test main function when fetch fails."""
    with patch.multiple(
        "arborist.cli",
        is_git_repo=lambda: True,
        fetch_and_prune=lambda progress_callback=None: raise_(GitError("Fetch failed")),
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
        get_merged_remote_branches=lambda: [],
        optimize_repo=lambda progress_callback=None: None,
    ):
        result = runner.invoke(cli.app)
        assert result.exit_code == 1  # Should exit with error
        assert "Error updating repository state: Fetch failed" in result.stdout
