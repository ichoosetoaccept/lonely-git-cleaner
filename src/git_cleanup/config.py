"""Configuration handling for git-cleanup."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration model for git-cleanup."""

    protected_branches: list[str] = Field(
        default=["main"],
        description="Branches that should never be deleted",
    )
    dry_run_by_default: bool = Field(
        default=False,
        description="Whether to run in dry-run mode by default",
    )
    interactive: bool = Field(
        default=False,
        description="Whether to prompt for confirmation before deleting branches",
    )
    skip_gc: bool = Field(
        default=False,
        description="Whether to skip garbage collection",
    )
    reflog_expiry: str = Field(
        default="90.days",
        description="How long to keep reflog entries",
    )


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".git-cleanuprc"


def load_config() -> Config:
    """Load configuration from file or return defaults."""
    config_path = get_config_path()

    try:
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                user_config = json.load(f)
                return Config(**user_config)
    except (json.JSONDecodeError, OSError) as e:
        # Log error but continue with defaults
        print(f"Warning: Error loading config file, using defaults ({e!s})")

    return Config()


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            # Write JSON in a single call
            json.dump(config.model_dump(), f, indent=2)
    except OSError as e:
        print(f"Error: Failed to save config file: {e!s}")
