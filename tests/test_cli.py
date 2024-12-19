"""Tests for CLI interface."""

from unittest.mock import patch

import pytest
from click.exceptions import Exit
from git_cleanup import cli, config, git
from typer.testing import CliRunner

runner = CliRunner()


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
    ):
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
    ):
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
    ):
        # Simulate user answering "n" to deletion prompt
        result = runner.invoke(cli.app, ["--interactive"], input="n\n")
        assert result.exit_code == 0
        assert "Delete branch feature/123?" in result.stdout


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
    ):
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
    ):
        result = runner.invoke(cli.app)
        assert result.exit_code == 0
        assert "Error deleting feature/123: test error" in result.stdout
