"""Tests for configuration handling."""

import os
from pathlib import Path
from typing import Generator

import pytest
from arborist.config import ArboristConfig
from arborist.errors import ConfigError, ErrorCode
from pydantic import ValidationError


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config file.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path

    Yields
    ------
    Path
        Path to temporary config file
    """
    config_file = tmp_path / ".arboristrc"
    yield config_file
    if config_file.exists():
        config_file.unlink()


def test_default_config() -> None:
    """Test default configuration values."""
    config = ArboristConfig()
    assert config.branch.protected_patterns == ["main", "master"]
    assert config.git.reflog_expiry == "90.days"
    assert not config.dry_run_by_default
    assert config.interactive
    assert config.log_level == "INFO"


def test_config_from_env() -> None:
    """Test configuration from environment variables."""
    os.environ["ARBORIST_BRANCH__PROTECTED_PATTERNS"] = '["develop", "staging"]'
    os.environ["ARBORIST_GIT__REFLOG_EXPIRY"] = "30.days"
    os.environ["ARBORIST_DRY_RUN_BY_DEFAULT"] = "true"
    os.environ["ARBORIST_LOG_LEVEL"] = "DEBUG"

    config = ArboristConfig()
    assert config.branch.protected_patterns == ["develop", "staging"]
    assert config.git.reflog_expiry == "30.days"
    assert config.dry_run_by_default
    assert config.log_level == "DEBUG"

    # Clean up
    del os.environ["ARBORIST_BRANCH__PROTECTED_PATTERNS"]
    del os.environ["ARBORIST_GIT__REFLOG_EXPIRY"]
    del os.environ["ARBORIST_DRY_RUN_BY_DEFAULT"]
    del os.environ["ARBORIST_LOG_LEVEL"]


def test_invalid_log_level() -> None:
    """Test validation of invalid log level."""
    with pytest.raises(ValidationError) as exc_info:
        ArboristConfig(log_level="INVALID")
    assert "Invalid log level" in str(exc_info.value)


def test_save_and_load_config(temp_config_file: Path) -> None:
    """Test saving and loading configuration.

    Parameters
    ----------
    temp_config_file : Path
        Path to temporary config file
    """
    # Create and save config
    config = ArboristConfig(
        branch={"protected_patterns": ["develop"]},
        git={"reflog_expiry": "60.days"},
        dry_run_by_default=True,
    )
    config.save_config(temp_config_file)

    # Load config
    loaded_config = ArboristConfig.load_config(str(temp_config_file))
    assert loaded_config.branch.protected_patterns == ["develop"]
    assert loaded_config.git.reflog_expiry == "60.days"
    assert loaded_config.dry_run_by_default


def test_load_nonexistent_config(temp_config_file: Path) -> None:
    """Test loading non-existent configuration.

    Parameters
    ----------
    temp_config_file : Path
        Path to temporary config file
    """
    # Load non-existent config should return default config
    config = ArboristConfig.load_config(str(temp_config_file))
    assert isinstance(config, ArboristConfig)
    assert config.branch.protected_patterns == ["main", "master"]


def test_save_config_permission_error(tmp_path: Path) -> None:
    """Test saving configuration with permission error.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path
    """
    # Create a directory where we want the config file
    config_path = tmp_path / ".arboristrc"
    config_path.mkdir()

    config = ArboristConfig()
    with pytest.raises(ConfigError) as exc_info:
        config.save_config(config_path)

    assert exc_info.value.code == ErrorCode.CONFIG_PERMISSION
    assert str(config_path) in exc_info.value.details


def test_load_invalid_config(temp_config_file: Path) -> None:
    """Test loading invalid configuration file.

    Parameters
    ----------
    temp_config_file : Path
        Path to temporary config file
    """
    # Create an invalid JSON file
    temp_config_file.write_text("{invalid json")

    with pytest.raises(ConfigError) as exc_info:
        ArboristConfig.load_config(str(temp_config_file))
    assert exc_info.value.code == ErrorCode.CONFIG_INVALID


def test_branch_name_pattern() -> None:
    """Test branch name pattern validation."""
    # Test valid pattern
    config = ArboristConfig(branch={"name_pattern": r"^feature/[a-z0-9-]+$"})
    assert config.branch.name_pattern == r"^feature/[a-z0-9-]+$"

    # Test invalid pattern (not a valid regex)
    with pytest.raises(ValidationError):
        ArboristConfig(branch={"name_pattern": "["})


def test_invalid_chars_config() -> None:
    """Test invalid characters configuration."""
    # Test custom invalid chars
    config = ArboristConfig(branch={"invalid_chars": ["#", "@"]})
    assert config.branch.invalid_chars == ["#", "@"]

    # Test empty list (allowing all characters)
    config = ArboristConfig(branch={"invalid_chars": []})
    assert config.branch.invalid_chars == []


def test_nested_env_config() -> None:
    """Test nested environment variable configuration."""
    os.environ["ARBORIST_BRANCH__NAME_PATTERN"] = r"^feature/[a-z0-9-]+$"
    os.environ["ARBORIST_BRANCH__INVALID_CHARS"] = '["#", "@"]'
    os.environ["ARBORIST_GIT__GC_AUTO"] = "false"

    config = ArboristConfig()
    assert config.branch.name_pattern == r"^feature/[a-z0-9-]+$"
    assert config.branch.invalid_chars == ["#", "@"]
    assert not config.git.gc_auto

    # Clean up
    del os.environ["ARBORIST_BRANCH__NAME_PATTERN"]
    del os.environ["ARBORIST_BRANCH__INVALID_CHARS"]
    del os.environ["ARBORIST_GIT__GC_AUTO"]


def test_config_precedence(temp_config_file: Path) -> None:
    """Test configuration precedence (env vars override file).

    Parameters
    ----------
    temp_config_file : Path
        Path to temporary config file
    """
    # Create config file
    config = ArboristConfig(
        branch={"protected_patterns": ["develop"]},
        git={"reflog_expiry": "60.days"},
    )
    config.save_config(temp_config_file)

    # Set environment variables
    os.environ["ARBORIST_BRANCH__PROTECTED_PATTERNS"] = '["main", "master"]'
    os.environ["ARBORIST_GIT__REFLOG_EXPIRY"] = "30.days"

    # Load config - env vars should take precedence
    loaded_config = ArboristConfig.load_config(str(temp_config_file))
    assert loaded_config.branch.protected_patterns == ["main", "master"]
    assert loaded_config.git.reflog_expiry == "30.days"

    # Clean up
    del os.environ["ARBORIST_BRANCH__PROTECTED_PATTERNS"]
    del os.environ["ARBORIST_GIT__REFLOG_EXPIRY"]
