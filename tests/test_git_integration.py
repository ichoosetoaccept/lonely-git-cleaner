"""Integration tests for git operations."""

from collections.abc import Generator
from pathlib import Path

import pytest

from arborist.git.repo import BranchStatus, GitRepo
from tests.git_test_env import GitTestEnv


@pytest.fixture(scope="function")
def git_test_env(tmp_path: Path) -> Generator[GitTestEnv, None, None]:
    """Create a test git environment."""
    env = GitTestEnv(tmp_path)
    yield env
    env.cleanup()


def test_complex_branch_cleanup(git_test_env: GitTestEnv) -> None:
    """Test cleanup of branches in a complex scenario."""
    # Create a develop branch
    git_test_env.create_branch("develop")
    git_test_env.create_commit()
    git_test_env.push_branch("develop")

    # Create feature branches merged into develop
    git_test_env.create_branch("feature/one")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/one", "develop")

    git_test_env.create_branch("feature/two")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/two", "develop")

    # Create a feature branch merged into main
    git_test_env.checkout_branch("main")
    git_test_env.create_branch("feature/main")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/main", "main")

    # Create some gone branches
    git_test_env.create_branch("feature/gone1")
    git_test_env.create_commit()
    git_test_env.push_branch("feature/gone1")
    git_test_env.delete_remote_branch("feature/gone1")

    git_test_env.create_branch("feature/gone2")
    git_test_env.create_commit()
    git_test_env.push_branch("feature/gone2")
    git_test_env.delete_remote_branch("feature/gone2")

    # Create some unmerged branches
    git_test_env.create_branch("feature/wip1")
    git_test_env.create_commit()

    git_test_env.create_branch("feature/wip2")
    git_test_env.create_commit()

    # Switch back to main
    git_test_env.checkout_branch("main")

    # Create repo instance
    repo = GitRepo(git_test_env.clone_dir)

    # Check initial branch status
    status = repo.get_branch_status()
    assert status["feature/one"] == BranchStatus.MERGED
    assert status["feature/two"] == BranchStatus.MERGED
    assert status["feature/main"] == BranchStatus.MERGED
    assert status["feature/gone1"] == BranchStatus.GONE
    assert status["feature/gone2"] == BranchStatus.GONE
    assert status["feature/wip1"] == BranchStatus.UNMERGED
    assert status["feature/wip2"] == BranchStatus.UNMERGED

    # Clean up with protection patterns
    repo.clean(
        protect=["main", "develop", "*wip*"],
        force=True,
        no_interactive=True,
        dry_run=False,
    )

    # Verify results
    heads = [h.name for h in repo.repo.heads]
    assert "main" in heads  # Protected explicitly
    assert "develop" in heads  # Protected explicitly
    assert "feature/wip1" in heads  # Protected by pattern
    assert "feature/wip2" in heads  # Protected by pattern
    assert "feature/one" not in heads  # Merged, should be deleted
    assert "feature/two" not in heads  # Merged, should be deleted
    assert "feature/main" not in heads  # Merged, should be deleted
    assert "feature/gone1" not in heads  # Gone, should be deleted
    assert "feature/gone2" not in heads  # Gone, should be deleted


def test_branch_cleanup_with_worktrees(git_test_env: GitTestEnv) -> None:
    """Test cleanup of branches with worktrees."""
    # Create and set up branches
    git_test_env.create_branch("feature/worktree")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/worktree", "main")

    # Create a worktree
    worktree_path = Path(git_test_env.temp_dir) / "worktree"
    git_test_env.repo.repo.git.worktree("add", str(worktree_path), "feature/worktree")

    # Create repo instance
    repo = GitRepo(git_test_env.clone_dir)

    # Clean up
    repo.clean(force=True, no_interactive=True)

    # Verify the branch was deleted and worktree removed
    assert "feature/worktree" not in [h.name for h in repo.repo.heads]
    assert not worktree_path.exists()


def test_branch_cleanup_with_remote_tracking(git_test_env: GitTestEnv) -> None:
    """Test cleanup with complex remote tracking scenarios."""
    # Create branches with different remote tracking setups
    git_test_env.create_branch("feature/tracked")
    git_test_env.create_commit()
    git_test_env.push_branch("feature/tracked")
    git_test_env.merge_branch("feature/tracked", "main")

    git_test_env.create_branch("feature/untracked")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/untracked", "main")

    git_test_env.create_branch("feature/diverged")
    git_test_env.create_commit()
    git_test_env.push_branch("feature/diverged")
    git_test_env.create_commit()  # Create another commit to diverge

    # Create repo instance
    repo = GitRepo(git_test_env.clone_dir)

    # Clean up
    repo.clean(force=True, no_interactive=True)

    # Verify results
    heads = [h.name for h in repo.repo.heads]
    assert "feature/tracked" not in heads  # Merged, should be deleted
    assert "feature/untracked" not in heads  # Merged, should be deleted
    assert "feature/diverged" in heads  # Diverged, should be kept


def test_branch_cleanup_with_complex_merges(git_test_env: GitTestEnv) -> None:
    """Test cleanup with complex merge scenarios."""
    # Create develop branch
    git_test_env.create_branch("develop")
    git_test_env.create_commit()

    # Create feature branch merged into develop
    git_test_env.create_branch("feature/dev")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/dev", "develop")

    # Merge develop into main
    git_test_env.checkout_branch("main")
    git_test_env.merge_branch("develop", "main")

    # Create feature branch merged into main
    git_test_env.create_branch("feature/main")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature/main", "main")

    # Create repo instance
    repo = GitRepo(git_test_env.clone_dir)

    # Clean up
    repo.clean(protect=["main", "develop"], force=True, no_interactive=True)

    # Verify results
    heads = [h.name for h in repo.repo.heads]
    assert "main" in heads  # Protected
    assert "develop" in heads  # Protected
    assert "feature/dev" not in heads  # Merged through develop into main
    assert "feature/main" not in heads  # Directly merged into main


def test_branch_cleanup_with_pattern_variations(git_test_env: GitTestEnv) -> None:
    """Test cleanup with various protection patterns."""
    # Create branches with different patterns
    branches = [
        "feature/one",
        "feature/two",
        "bugfix/one",
        "bugfix/two",
        "release/1.0",
        "release/2.0",
        "hotfix/1",
        "hotfix/2",
        "experimental/test",
    ]

    # Create and merge all branches
    for branch in branches:
        git_test_env.create_branch(branch)
        git_test_env.create_commit()
        git_test_env.merge_branch(branch, "main")

    # Create repo instance
    repo = GitRepo(git_test_env.clone_dir)

    # Clean up with various protection patterns
    protect = [
        "main",
        "feature/*",  # Protect all feature branches
        "release/1.*",  # Protect release 1.x
        "hotfix/*1",  # Protect hotfixes ending in 1
        "*test",  # Protect anything ending in test
    ]

    repo.clean(protect=protect, force=True, no_interactive=True)

    # Verify results
    heads = [h.name for h in repo.repo.heads]
    assert "main" in heads  # Protected explicitly
    assert "feature/one" in heads  # Protected by feature/*
    assert "feature/two" in heads  # Protected by feature/*
    assert "release/1.0" in heads  # Protected by release/1.*
    assert "release/2.0" not in heads  # Not protected
    assert "hotfix/1" in heads  # Protected by hotfix/*1
    assert "hotfix/2" not in heads  # Not protected
    assert "experimental/test" in heads  # Protected by *test
    assert "bugfix/one" not in heads  # Not protected
    assert "bugfix/two" not in heads  # Not protected
