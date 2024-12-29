"""Tests for configuration handling."""

import json

import pytest

from arborist.config import Config, ConfigError, load_config


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary directory for config files."""
    return tmp_path


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.protected_branches == ["main"]
    assert not config.dry_run_by_default
    assert config.interactive
    assert not config.skip_gc
    assert config.reflog_expiry == "90.days"


def test_load_config_no_file():
    """Test loading config when file doesn't exist."""
    config = load_config("/nonexistent/path")
    assert isinstance(config, Config)
    assert config.protected_branches == ["main"]


def test_load_config_with_file(config_dir):
    """Test loading config from file."""
    config_path = config_dir / ".arboristrc"
    test_config = {
        "protected_branches": ["main", "develop"],
        "dry_run_by_default": True,
        "interactive": False,
        "skip_gc": True,
        "reflog_expiry": "30.days",
    }
    config_path.write_text(json.dumps(test_config))

    config = load_config(str(config_path))
    assert config.protected_branches == ["main", "develop"]
    assert config.dry_run_by_default
    assert not config.interactive
    assert config.skip_gc
    assert config.reflog_expiry == "30.days"


def test_load_config_invalid_json(config_dir):
    """Test loading config with invalid JSON."""
    config_path = config_dir / ".arboristrc"
    config_path.write_text("invalid json")

    with pytest.raises(ConfigError):
        load_config(str(config_path))


def test_save_config(config_dir):
    """Test saving config to file."""
    config = Config(
        protected_branches=["main", "develop"],
        dry_run_by_default=True,
        interactive=False,
        skip_gc=True,
        reflog_expiry="30.days",
    )
    config_path = config_dir / ".arboristrc"
    config.save_config(config_path)

    # Load and verify
    loaded_config = load_config(str(config_path))
    assert loaded_config.protected_branches == ["main", "develop"]
    assert loaded_config.dry_run_by_default
    assert not loaded_config.interactive
    assert loaded_config.skip_gc
    assert loaded_config.reflog_expiry == "30.days"


def test_save_config_error(config_dir):
    """Test error handling when saving config."""
    config = Config()
    config_path = config_dir / ".arboristrc"
    config_path.mkdir()  # Create a directory instead of a file

    with pytest.raises(ConfigError):
        config.save_config(config_path)
