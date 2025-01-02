"""Test fixtures and helper functions."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from git.exc import GitCommandError
from git.repo.base import Repo


@pytest.fixture
def temp_repo() -> Generator[Repo, None, None]:
    """Create a temporary git repository.

    Yields
    -------
    Repo
        GitPython repository instance
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repository
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)

        # Configure repository
        repo.git.config("core.autocrlf", "false")
        repo.git.config("core.safecrlf", "true")
        repo.git.config("core.filemode", "false")

        # Configure git user
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create initial commit
        readme_path = repo_path / "README.md"
        readme_path.write_text("# Test Repository")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Create main branch
        repo.git.branch("-m", "main")

        yield repo

        # Clean up any remaining changes
        try:
            repo.git.reset("--hard")
            repo.git.clean("-fd")
        except GitCommandError:
            pass
