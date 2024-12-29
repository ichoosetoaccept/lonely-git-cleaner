"""Configuration management for git branch cleanup."""

import json
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    """Configuration for git branch cleanup."""

    protected_branches: list[str] = ["main"]
    dry_run_by_default: bool = False
    interactive: bool = False
    skip_gc: bool = False
    reflog_expiry: str = "90.days"

    @staticmethod
    def get_config_path() -> Path:
        """Get the path to the configuration file."""
        return Path.home() / ".git-cleanuprc"

    @staticmethod
    def save_config(config: "Config") -> None:
        """Save configuration to file."""
        config_path = Config.get_config_path()

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, indent=2)
        except OSError as e:
            print(f"Error: Failed to save config file: {e!s}")


def load_config() -> Config:
    """Load configuration from file or return defaults."""
    config_path = Config.get_config_path()

    try:
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                user_config = json.load(f)
                return Config(**user_config)
    except (json.JSONDecodeError, OSError) as e:
        # Log error but continue with defaults
        print(f"Warning: Error loading config file, using defaults ({e!s})")

    return Config()
