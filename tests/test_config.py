"""Test configuration functionality."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

from arborist.config import Config, load_config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.protected_branches == ["main"]
    assert not config.dry_run_by_default
    assert not config.interactive
    assert not config.skip_gc
    assert config.reflog_expiry == "90.days"


def test_get_config_path():
    """Test getting config file path."""
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = Path("/home/user")
        path = Config.get_config_path()
        assert path == Path("/home/user/.git-cleanuprc")


def test_load_config_no_file():
    """Test loading config when file doesn't exist."""
    with patch("pathlib.Path.exists", return_value=False):
        config = load_config()
        assert isinstance(config, Config)
        assert config.protected_branches == ["main"]


def test_load_config_with_file():
    """Test loading config from file."""
    config_data = {
        "protected_branches": ["main", "develop"],
        "dry_run_by_default": True,
        "interactive": True,
        "skip_gc": True,
        "reflog_expiry": "30.days",
    }
    mock_file = mock_open(read_data=json.dumps(config_data))

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "builtins.open",
            mock_file,
        ),
    ):
        config = load_config()
        assert config.protected_branches == ["main", "develop"]
        assert config.dry_run_by_default
        assert config.interactive
        assert config.skip_gc
        assert config.reflog_expiry == "30.days"


def test_load_config_invalid_json():
    """Test loading config with invalid JSON."""
    mock_file = mock_open(read_data="invalid json")

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "builtins.open",
            mock_file,
        ),
    ):
        config = load_config()
        assert isinstance(config, Config)
        assert config.protected_branches == ["main"]


def test_save_config():
    """Test saving configuration to file."""
    config = Config(
        protected_branches=["main", "develop"],
        dry_run_by_default=True,
        interactive=True,
        skip_gc=True,
        reflog_expiry="30.days",
    )
    mock_file = mock_open()

    with patch("builtins.open", mock_file):
        Config.save_config(config)

    mock_file.assert_called_once()
    handle = mock_file()
    # Convert config to dict and compare with expected values
    expected_data = {
        "protected_branches": ["main", "develop"],
        "dry_run_by_default": True,
        "interactive": True,
        "skip_gc": True,
        "reflog_expiry": "30.days",
    }
    # Combine all write calls into a single string
    written_data = ""
    for call_args in handle.write.call_args_list:
        written_data += call_args[0][0]
    assert json.loads(written_data) == expected_data


def test_save_config_error():
    """Test error handling when saving config."""
    config = Config()
    mock_file = mock_open()
    mock_file.side_effect = OSError("Permission denied")

    with patch("builtins.open", mock_file):
        # Should not raise exception
        Config.save_config(config)
