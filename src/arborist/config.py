"""Configuration handling for arborist."""

from pathlib import Path

from pydantic import BaseModel


class ConfigError(Exception):
    """Configuration error."""

    pass


class Config(BaseModel):
    """Configuration for arborist."""

    protected_branches: list[str] = ["main"]
    dry_run_by_default: bool = False
    interactive: bool = True
    skip_gc: bool = False
    reflog_expiry: str = "90.days"

    def save_config(self, path: Path | None = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = Path.home() / ".arboristrc"
        try:
            path.write_text(self.model_dump_json(indent=2))
        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}") from e


def load_config(path: str | None = None) -> Config:
    """Load configuration from file."""
    if path is None:
        path = str(Path.home() / ".arboristrc")
    try:
        config_path = Path(path)
        if config_path.exists():
            return Config.model_validate_json(config_path.read_text())
        return Config()
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}") from e
