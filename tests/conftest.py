"""Test configuration and fixtures."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .git_test_env import GitTestEnv


@pytest.fixture
def tmp_git_repo() -> Generator[GitTestEnv, None, None]:
    """Create a temporary git repository for testing."""
    env = GitTestEnv()
    yield env
    env.cleanup()


@pytest.fixture
def tmp_path() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    path = Path(tempfile.mkdtemp())
    yield path
    if path.exists():
        for item in path.iterdir():
            if item.is_file():
                item.unlink()
            else:
                item.rmdir()
        path.rmdir()


@pytest.fixture
def tmp_file():
    """Create a temporary file for testing."""
    tmp = tempfile.mktemp()
    yield Path(tmp)
    if os.path.exists(tmp):
        os.unlink(tmp)
