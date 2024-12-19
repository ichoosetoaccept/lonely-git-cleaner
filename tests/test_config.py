"""Tests for config module."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

from git_cleanup import config


def test_config_defaults():
    """Test default configuration values."""
    cfg = config.Config()
    assert cfg.protected_branches == ["main", "master"]
    assert not cfg.dry_run_by_default
    assert not cfg.interactive
    assert not cfg.skip_gc
    assert cfg.reflog_expiry == "90.days"


def test_get_config_path():
    """Test config path is in home directory."""
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = Path("/home/user")
        path = config.get_config_path()
        assert path == Path("/home/user/.git-cleanuprc")


def test_load_config_no_file():
    """Test loading config when file doesn't exist."""
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        cfg = config.load_config()
        assert isinstance(cfg, config.Config)
        # Should return defaults
        assert cfg.protected_branches == ["main", "master"]


def test_load_config_with_file():
    """Test loading config from existing file."""
    test_config = {
        "protected_branches": ["develop"],
        "dry_run_by_default": True,
        "interactive": True,
        "skip_gc": True,
        "reflog_expiry": "30.days",
    }

    mock_file = mock_open(read_data=json.dumps(test_config))
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", mock_file):
            cfg = config.load_config()

            assert cfg.protected_branches == ["develop"]
            assert cfg.dry_run_by_default
            assert cfg.interactive
            assert cfg.skip_gc
            assert cfg.reflog_expiry == "30.days"


def test_load_config_invalid_json():
    """Test loading config with invalid JSON."""
    mock_file = mock_open(read_data="invalid json")
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", mock_file):
            cfg = config.load_config()
            # Should return defaults on error
            assert cfg.protected_branches == ["main", "master"]


def test_save_config():
    """Test saving configuration to file."""
    cfg = config.Config(protected_branches=["develop"])
    mock_file = mock_open()

    with patch("builtins.open", mock_file):
        config.save_config(cfg)

        # Get all write calls
        write_calls = mock_file().write.call_args_list
        written_content = ''.join(call.args[0] for call in write_calls)

        # Parse and verify the written JSON
        saved_config = json.loads(written_content)
        assert saved_config["protected_branches"] == ["develop"]
        assert not saved_config["dry_run_by_default"]
        assert not saved_config["interactive"]
        assert not saved_config["skip_gc"]
        assert saved_config["reflog_expiry"] == "90.days"


def test_save_config_error():
    """Test handling save errors gracefully."""
    cfg = config.Config()
    mock_file = mock_open()
    mock_file.side_effect = OSError("Permission denied")

    with patch("builtins.open", mock_file):
        # Should not raise exception
        config.save_config(cfg)
