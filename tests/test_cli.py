"""Tests for CLI interface."""

from unittest.mock import call, patch

import pytest
from click.exceptions import Exit
from git_cleanup import cli, config, git
from typer.testing import CliRunner

runner = CliRunner()

# Constants for test cases
EXPECTED_FETCH_PRUNE_STEPS = 2  # Fetching and pruning steps
EXPECTED_OPTIMIZE_STEPS = 3  # Pruning, GC, and completion steps
EXPECTED_CONFIRM_STEPS = 3  # Bulk confirm + per branch confirms
EXPECTED_CONFIRM_STEPS_TWO_BRANCHES = 3  # Global + two branches
EXPECTED_CONFIRM_STEPS_ONE_BRANCH = 2  # Global + one branch
EXPECTED_DELETE_STEPS_TWO_BRANCHES = 2  # Two branches to delete


@pytest.fixture
def mock_config():
    """Fixture to mock config loading."""
    with patch("git_cleanup.config.load_config") as mock:
        mock.return_value = config.Config()
        yield mock


@pytest.fixture
def mock_git():
    """Fixture to mock git operations."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        fetch_and_prune=lambda progress_callback=None: None,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
        optimize_repo=lambda progress_callback=None: None,
        delete_branch=lambda *args, **kwargs: None,
    ) as mocks:
        yield mocks


@pytest.fixture
def config_fixture():
    """Fixture to provide a test configuration."""
    return config.Config()


def test_validate_git_repo():
    """Test git repository validation."""
    with patch("git_cleanup.git.is_git_repo", return_value=False):
        with pytest.raises(Exit):
            cli.validate_git_repo()


def test_main_not_git_repo(mock_config):
    """Test handling non-git repository."""
    with patch("git_cleanup.git.is_git_repo", return_value=False):
        result = runner.invoke(cli.app)
        assert result.exit_code == 1
        assert "Error: Not a git repository" in result.stdout


def test_main_no_branches(mock_config, mock_git):
    """Test when no branches to clean."""
    with patch("git_cleanup.git.is_git_repo", return_value=True):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "No branches with gone remotes found" in result.stdout
        assert "No merged branches found" in result.stdout


def test_main_with_gone_branches(mock_config):
    """Test cleaning gone branches."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: ["feature/123"],
        get_merged_branches=lambda: [],
        delete_branch=lambda *args, **kwargs: None,
    ), patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Found 1 branches with gone remotes" in result.stdout


def test_main_with_merged_branches(mock_config):
    """Test cleaning merged branches."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: ["feature/456", "hotfix/789"],
        delete_branch=lambda *args, **kwargs: None,
    ), patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Found 2 merged branches" in result.stdout


def test_main_dry_run(mock_config, mock_git):
    """Test dry run mode."""
    result = runner.invoke(cli.app, ["--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN: No changes will be made" in result.stdout


def test_main_interactive_mode(mock_config):
    """Test interactive mode."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: ["feature/123"],
        get_merged_branches=lambda: [],
        delete_branch=lambda *args, **kwargs: None,
    ), patch("rich.prompt.Confirm.ask", side_effect=[True, False]):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Skipping branch feature/123" in result.stdout


def test_fetch_prune_progress(mock_config):
    """Test progress bar during fetch and prune operations."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
    ), patch("git_cleanup.git.fetch_and_prune") as mock_fetch:
        result = runner.invoke(cli.app)
        assert result.exit_code == 0

        # Verify fetch_and_prune was called with a progress callback
        assert mock_fetch.call_count == 1
        progress_callback = mock_fetch.call_args[1]["progress_callback"]
        assert callable(progress_callback)

        # Test the progress messages
        with patch("rich.progress.Progress.update") as mock_update:
            progress_callback("Fetching from remotes...")
            progress_callback("Pruning old references...")

            expected_fetch_prune_steps = 2  # Fetching and pruning steps
            assert mock_update.call_count == expected_fetch_prune_steps
            assert "🔄 Fetching from remotes..." in str(mock_update.call_args_list[0])
            assert "🔄 Pruning old references..." in str(mock_update.call_args_list[1])


def test_optimize_progress(mock_config):
    """Test progress bar during repository optimization."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
    ), patch("git_cleanup.git.optimize_repo") as mock_optimize:
        result = runner.invoke(cli.app)
        assert result.exit_code == 0

        # Verify optimize_repo was called with a progress callback
        assert mock_optimize.call_count == 1
        progress_callback = mock_optimize.call_args[1]["progress_callback"]
        assert callable(progress_callback)

        # Test the progress messages
        with patch("rich.progress.Progress.update") as mock_update:
            progress_callback("Pruning unreachable objects...")
            progress_callback("Running garbage collection...")
            progress_callback("Repository optimization complete")

            expected_optimize_steps = 3  # Pruning, GC, and completion steps
            assert mock_update.call_count == expected_optimize_steps
            assert "⚡ Pruning unreachable objects..." in str(
                mock_update.call_args_list[0],
            )
            assert "⚡ Running garbage collection..." in str(
                mock_update.call_args_list[1],
            )
            assert "⚡ Repository optimization complete" in str(
                mock_update.call_args_list[2],
            )


def test_main_no_gc(mock_config):
    """Test skipping garbage collection."""
    mock_optimize = patch("git_cleanup.git.optimize_repo").start()
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
    ):
        result = runner.invoke(cli.app, ["--no-gc"])
        assert result.exit_code == 0
        mock_optimize.assert_not_called()
    patch.stopall()


def test_parse_protect_option():
    """Test parsing of protect option."""
    assert cli.parse_protect_option("") == []
    assert cli.parse_protect_option("main") == ["main"]
    assert cli.parse_protect_option("main,develop") == ["main", "develop"]
    assert cli.parse_protect_option(" main , develop ") == ["main", "develop"]


def test_main_protect_branches(mock_config):
    """Test protecting additional branches."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: ["develop", "feature/123", "staging"],
        get_merged_branches=lambda: [],
        filter_protected_branches=git.filter_protected_branches,
        delete_branch=lambda *args, **kwargs: None,
    ), patch("rich.prompt.Confirm.ask", return_value=True):
        # Test single branch protection
        result = runner.invoke(cli.app, ["--protect", "develop"])
        assert result.exit_code == 0
        assert "Found 2 branches with gone remotes" in result.stdout

        # Test comma-separated branch protection
        result = runner.invoke(cli.app, ["--protect", "develop,staging"])
        assert result.exit_code == 0
        assert "Found 1 branches with gone remotes" in result.stdout


def test_main_error_handling(mock_config):
    """Test handling git errors."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: ["feature/123"],
        delete_branch=lambda *args, **kwargs: exec('raise git.GitError("test error")'),
    ), patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Error deleting feature/123: test error" in result.stdout


def test_delete_branches_interactive_bulk_reject(mock_config):
    """Test rejecting all branch deletions at bulk prompt."""
    with patch("rich.prompt.Confirm.ask", return_value=False) as mock_confirm:
        branches = ["feature/123", "feature/456"]
        cli.delete_branches(branches, interactive=True)

        # Should only ask once for bulk confirmation
        expected_prompt = "\n[yellow]Do you want to proceed with deletion?[/yellow]"
        mock_confirm.assert_called_once_with(expected_prompt, default=False)


def test_delete_branches_interactive_individual_choices(mock_config):
    """Test mixed acceptance/rejection of individual branches."""
    # Mock the bulk confirmation to return True
    # Then alternate between True/False for individual branches
    confirm_responses = [True, True, False]
    with patch(
        "rich.prompt.Confirm.ask",
        side_effect=confirm_responses,
    ) as mock_confirm:
        with patch("git_cleanup.git.delete_branch") as mock_delete:
            branches = ["feature/123", "feature/456"]
            cli.delete_branches(branches, interactive=True)

            # Should be called for bulk and individual confirmations
            assert mock_confirm.call_count == EXPECTED_CONFIRM_STEPS

            # Should only delete the first branch
            mock_delete.assert_called_once_with("feature/123", force=False)


def test_delete_branches_non_interactive(mock_config):
    """Test non-interactive branch deletion."""
    with patch("rich.prompt.Confirm.ask") as mock_confirm:
        with patch("git_cleanup.git.delete_branch") as mock_delete:
            branches = ["feature/123", "feature/456"]
            cli.delete_branches(branches, interactive=False)

            # Should not ask for any confirmation
            mock_confirm.assert_not_called()

            # Should delete all branches
            assert mock_delete.call_count == EXPECTED_FETCH_PRUNE_STEPS
            mock_delete.assert_has_calls(
                [
                    call("feature/123", force=False),
                    call("feature/456", force=False),
                ],
            )


def test_handle_merged_remote_branches_none_found(mocker, config_fixture):
    """Test handling merged remote branches when none are found."""
    mock_get_merged = mocker.patch(
        "git_cleanup.git.get_merged_remote_branches",
        return_value=[],
    )
    mock_filter = mocker.patch(
        "git_cleanup.git.filter_protected_branches",
        return_value=[],
    )
    mock_delete = mocker.patch("git_cleanup.cli.delete_remote_branches")

    cli.handle_merged_remote_branches(config_fixture)

    mock_get_merged.assert_called_once()
    mock_filter.assert_called_once_with([], config_fixture.protected_branches)
    mock_delete.assert_not_called()


def test_handle_merged_remote_branches_found(mocker, config_fixture):
    """Test handling merged remote branches when some are found."""
    mock_get_merged = mocker.patch(
        "git_cleanup.git.get_merged_remote_branches",
        return_value=["feature-1", "feature-2"],
    )
    mock_filter = mocker.patch(
        "git_cleanup.git.filter_protected_branches",
        return_value=["feature-1", "feature-2"],
    )
    mock_delete = mocker.patch("git_cleanup.cli.delete_remote_branches")

    cli.handle_merged_remote_branches(config_fixture)

    mock_get_merged.assert_called_once()
    mock_filter.assert_called_once_with(
        ["feature-1", "feature-2"],
        config_fixture.protected_branches,
    )
    mock_delete.assert_called_once_with(
        ["feature-1", "feature-2"],
        config_fixture.interactive,
    )


def test_handle_merged_remote_branches_dry_run(mocker, config_fixture):
    """Test handling merged remote branches in dry run mode."""
    config_fixture.dry_run_by_default = True
    mock_get_merged = mocker.patch(
        "git_cleanup.git.get_merged_remote_branches",
        return_value=["feature-1", "feature-2"],
    )
    mock_filter = mocker.patch(
        "git_cleanup.git.filter_protected_branches",
        return_value=["feature-1", "feature-2"],
    )
    mock_delete = mocker.patch("git_cleanup.cli.delete_remote_branches")

    cli.handle_merged_remote_branches(config_fixture)

    mock_get_merged.assert_called_once()
    mock_filter.assert_called_once_with(
        ["feature-1", "feature-2"],
        config_fixture.protected_branches,
    )
    mock_delete.assert_not_called()


def test_delete_remote_branches_none(mocker):
    """Test deleting remote branches when none are provided."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask")
    mock_delete = mocker.patch("git_cleanup.git.delete_remote_branch")

    cli.delete_remote_branches([])

    mock_confirm.assert_not_called()
    mock_delete.assert_not_called()


def test_delete_remote_branches_non_interactive(mocker):
    """Test deleting remote branches in non-interactive mode."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask")
    mock_delete = mocker.patch("git_cleanup.git.delete_remote_branch")

    cli.delete_remote_branches(["feature-1", "feature-2"], interactive=False)

    mock_confirm.assert_not_called()
    mock_delete.assert_has_calls(
        [
            mocker.call("feature-1"),
            mocker.call("feature-2"),
        ],
    )


def test_delete_remote_branches_interactive_confirm(mocker):
    """Test deleting remote branches with interactive confirmation."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=True)
    mock_delete = mocker.patch("git_cleanup.git.delete_remote_branch")

    cli.delete_remote_branches(["feature-1", "feature-2"], interactive=True)

    assert mock_confirm.call_count == EXPECTED_CONFIRM_STEPS  # Global + per branch
    mock_delete.assert_has_calls(
        [
            mocker.call("feature-1"),
            mocker.call("feature-2"),
        ],
    )


def test_delete_remote_branches_interactive_reject(mocker):
    """Test rejecting remote branch deletion in interactive mode."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=False)
    mock_delete = mocker.patch("git_cleanup.git.delete_remote_branch")

    cli.delete_remote_branches(["feature-1", "feature-2"], interactive=True)

    mock_confirm.assert_called_once()  # Only global confirmation
    mock_delete.assert_not_called()


def test_delete_remote_branches_error_handling(mocker):
    """Test error handling during remote branch deletion."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=True)
    mock_delete = mocker.patch(
        "git_cleanup.git.delete_remote_branch",
        side_effect=git.GitError("Remote branch deletion failed"),
    )

    cli.delete_remote_branches(["feature-1"], interactive=True)

    assert mock_confirm.call_count == EXPECTED_CONFIRM_STEPS_ONE_BRANCH
    mock_delete.assert_called_once_with("feature-1")


def test_delete_branches_error_handling(mocker):
    """Test error handling during branch deletion."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=True)
    mock_delete = mocker.patch(
        "git_cleanup.git.delete_branch",
        side_effect=git.GitError("Branch deletion failed"),
    )

    cli.delete_branches(["feature-1"], interactive=True)

    assert mock_confirm.call_count == EXPECTED_CONFIRM_STEPS_ONE_BRANCH
    mock_delete.assert_called_once_with("feature-1", force=False)


def test_main_with_all_options(mock_config):
    """Test main function with all options enabled."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: ["feature/123"],
        get_merged_branches=lambda: ["feature/456"],
        get_merged_remote_branches=lambda: ["feature/789"],
        delete_branch=lambda *args, **kwargs: None,
        delete_remote_branch=lambda *args, **kwargs: None,
    ), patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(
            cli.app,
            [
                "--dry-run",
                "--no-interactive",
                "--no-gc",
                "--protect",
                "main,develop",
            ],
        )
        assert result.exit_code == 0
        assert "DRY RUN: No changes will be made" in result.stdout


def test_main_with_optimize_error(mock_config):
    """Test main function when optimization fails."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
        get_merged_remote_branches=lambda: [],
        optimize_repo=lambda progress_callback=None: exec(
            'raise git.GitError("GC failed")',
        ),
    ):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Error optimizing repository: GC failed" in result.stdout


def test_delete_branches_with_error_and_continue(mocker):
    """Test branch deletion with error on one branch but continuing."""
    mock_confirm = mocker.patch("rich.prompt.Confirm.ask", return_value=True)
    mock_delete = mocker.patch(
        "git_cleanup.git.delete_branch",
        side_effect=[git.GitError("First failed"), None],
    )

    cli.delete_branches(["feature-1", "feature-2"], interactive=True)

    assert (
        mock_confirm.call_count == EXPECTED_CONFIRM_STEPS_TWO_BRANCHES
    )  # Global + both branches
    assert mock_delete.call_count == EXPECTED_DELETE_STEPS_TWO_BRANCHES
    mock_delete.assert_has_calls(
        [
            call("feature-1", force=False),
            call("feature-2", force=False),
        ],
    )


def test_main_with_fetch_error(mock_config):
    """Test main function when fetch fails."""
    with patch.multiple(
        "git_cleanup.git",
        is_git_repo=lambda: True,
        fetch_and_prune=lambda progress_callback=None: exec(
            'raise git.GitError("Fetch failed")',
        ),
        get_gone_branches=lambda: [],
        get_merged_branches=lambda: [],
        get_merged_remote_branches=lambda: [],
    ):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Fetch failed" in result.stdout
