"""Test fixtures and helper functions."""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from git import Repo


@pytest.fixture
def temp_repo() -> Generator[Repo, None, None]:
    """Create a temporary git repository with a remote.

    Yields
    -------
    Repo
        GitPython repository instance
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Resolve the real path to handle macOS /private prefix
        temp_dir = os.path.realpath(temp_dir)

        # Initialize local git repository
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()
        repo = Repo.init(repo_path)  # Initialize without specifying branch

        # Configure repository
        repo.git.config("core.autocrlf", "false")
        repo.git.config("core.safecrlf", "true")
        repo.git.config("core.filemode", "false")

        # Configure git user
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create and check out main branch
        repo.git.checkout("-b", "main")

        # Create initial commit on main
        readme = repo_path / "README.md"
        readme.write_text("# Test Repository")
        repo.index.add([str(readme)])
        repo.index.commit("Initial commit")

        # Create and configure a "remote" repository
        remote_path = Path(temp_dir) / "remote"
        remote_path.mkdir()
        Repo.init(remote_path, bare=True)
        repo.create_remote("origin", str(remote_path))

        # Push main branch to remote and set upstream tracking
        repo.git.push("-u", "origin", "main")  # Push and set upstream tracking

        yield repo
