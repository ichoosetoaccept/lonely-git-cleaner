"""Test git operations."""

from collections.abc import Generator
from pathlib import Path

import pytest
from git import Repo
from git.exc import GitCommandError

from arborist.exceptions import GitError
from arborist.git.repo import BranchStatus, GitRepo
from tests.git_test_env import GitTestEnv, create_file_in_repo


@pytest.fixture(scope="function")
def git_test_env(tmp_path: Path) -> Generator[GitTestEnv, None, None]:
    """Create a test git environment."""
    env = GitTestEnv(tmp_path)
    yield env
    env.cleanup()


def test_create_branch_from_head(git_test_env: GitTestEnv) -> None:
    """Test that we can create a branch from HEAD."""
    git_test_env.repo.create_branch("test_branch")
    assert "test_branch" in git_test_env.repo.repo.heads


def test_create_branch_from_non_head(git_test_env: GitTestEnv) -> None:
    """Test that we can create a branch from a non-HEAD commit."""
    # Create a commit on the main branch
    create_file_in_repo(git_test_env.repo_dir, "file1.txt", "content1")
    git_test_env.repo.repo.index.add(["file1.txt"])
    main_commit = git_test_env.repo.repo.index.commit("Initial commit")

    # Create a new branch from the initial commit
    git_test_env.repo.create_branch("test_branch", main_commit.hexsha)
    assert "test_branch" in git_test_env.repo.repo.heads

    # Switch to the new branch and verify its start point
    git_test_env.repo.repo.heads["test_branch"].checkout()
    assert git_test_env.repo.repo.head.commit == main_commit


def test_create_branch_invalid_start_point(git_test_env: GitTestEnv) -> None:
    """Test creating a branch from an invalid start point."""
    with pytest.raises(GitError, match="Failed to create branch"):
        git_test_env.repo.create_branch("test_branch", "nonexistent")


def test_get_branch_status(git_test_env: GitTestEnv) -> None:
    """Test getting branch status."""
    # Create a branch and commit
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.push_branch("feature")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Check branch status
    status = repo.get_branch_status()
    assert "feature" in status
    assert status["feature"] == BranchStatus.UNMERGED

    # Merge the branch
    git_test_env.merge_branch("feature", "main")
    status = repo.get_branch_status()
    assert status["feature"] == BranchStatus.MERGED

    # Delete remote branch
    git_test_env.delete_remote_branch("feature")
    status = repo.get_branch_status()
    assert status["feature"] == BranchStatus.GONE


def test_get_branch_status_with_no_remote(git_test_env: GitTestEnv) -> None:
    """Test getting branch status when there's no remote."""
    # Create a branch without pushing
    git_test_env.create_branch("feature")
    git_test_env.create_commit()

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Check branch status
    status = repo.get_branch_status()
    assert "feature" in status
    assert status["feature"] == BranchStatus.UNMERGED


def test_get_branch_status_with_invalid_remote(git_test_env: GitTestEnv) -> None:
    """Test getting branch status with an invalid remote."""
    # Create a branch and push it
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.push_branch("feature")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Corrupt the remote URL
    repo.repo.git.remote("set-url", "origin", "/nonexistent/path")

    # Check branch status
    status = repo.get_branch_status()
    assert "feature" in status
    assert status["feature"] == BranchStatus.UNKNOWN


def test_get_merged_branches(git_test_env: GitTestEnv) -> None:
    """Test getting merged branches."""
    # Create and merge a branch
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature", "main")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Check merged branches
    merged = repo.get_merged_branches()
    assert "feature" in merged


def test_get_merged_branches_with_multiple_targets(git_test_env: GitTestEnv) -> None:
    """Test getting merged branches with multiple target branches."""
    # Create develop branch
    git_test_env.create_branch("develop")
    git_test_env.create_commit()

    # Create and merge a feature branch into develop
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.merge_branch("feature", "develop")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Check merged branches
    merged = repo.get_merged_branches()
    assert "feature" in merged


def test_get_gone_branches(git_test_env: GitTestEnv) -> None:
    """Test getting gone branches."""
    # Create a branch and push it
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.push_branch("feature")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Delete remote branch
    git_test_env.delete_remote_branch("feature")

    # Check gone branches
    gone = repo.get_gone_branches()
    assert "feature" in gone


def test_get_gone_branches_with_multiple_remotes(git_test_env: GitTestEnv) -> None:
    """Test getting gone branches with multiple remotes."""
    # Create and push a branch
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.push_branch("feature")

    # Add another remote
    repo = GitRepo(git_test_env.clone_dir)
    repo.repo.create_remote("upstream", git_test_env.origin_dir)

    # Delete from origin
    git_test_env.delete_remote_branch("feature")

    # Check gone branches
    gone = repo.get_gone_branches()
    assert "feature" in gone


def test_delete_branch(git_test_env: GitTestEnv) -> None:
    """Test deleting a branch."""
    # Create a branch but stay on main
    git_test_env.create_branch("feature", checkout=False)
    git_test_env.checkout_branch("feature")
    git_test_env.create_commit()
    git_test_env.checkout_branch("main")

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Delete the branch
    repo.delete_branch("feature", force=True)
    assert "feature" not in [b.name for b in repo.repo.heads]


def test_delete_nonexistent_branch(git_test_env: GitTestEnv) -> None:
    """Test deleting a nonexistent branch."""
    repo = GitRepo(git_test_env.clone_dir)
    with pytest.raises(GitError, match="does not exist"):
        repo.delete_branch("nonexistent")


def test_delete_current_branch(git_test_env: GitTestEnv) -> None:
    """Test deleting the current branch."""
    # Create branches
    git_test_env.create_branch("feature")
    git_test_env.create_commit()
    git_test_env.create_branch("other")
    git_test_env.create_commit()

    # Create a repo object
    repo = GitRepo(git_test_env.clone_dir)

    # Try to delete the current branch
    with pytest.raises(GitError, match="Cannot delete current branch"):
        repo.delete_branch("other")

    # Switch to main and delete other branches
    git_test_env.checkout_branch("main")
    repo.delete_branch("feature", force=True)
    repo.delete_branch("other", force=True)
    assert "feature" not in [b.name for b in repo.repo.heads]
    assert "other" not in [b.name for b in repo.repo.heads]


def test_delete_protected_branch(git_test_env: GitTestEnv) -> None:
    """Test deleting a protected branch."""
    repo = GitRepo(git_test_env.clone_dir)
    with pytest.raises(GitError, match="Cannot delete branch main"):
        repo.delete_branch("main")


def test_get_current_branch_name(git_test_env: GitTestEnv) -> None:
    """Test that we can get the current branch name."""
    assert git_test_env.repo.get_current_branch_name() == "main"


def test_get_latest_commit_sha(git_test_env: GitTestEnv) -> None:
    """Test that we can get the latest commit SHA for a branch."""
    # Create a commit on the main branch
    create_file_in_repo(git_test_env.repo_dir, "file1.txt", "content1")
    git_test_env.repo.repo.index.add(["file1.txt"])
    commit = git_test_env.repo.repo.index.commit("Initial commit")

    # Get the latest commit SHA for the main branch
    latest_commit_sha = git_test_env.repo.get_latest_commit_sha("main")
    assert latest_commit_sha == commit.hexsha


def test_get_latest_commit_sha_for_nonexistent_branch(git_test_env: GitTestEnv) -> None:
    """Test getting the latest commit SHA for a nonexistent branch."""
    with pytest.raises(ValueError, match="Branch 'nonexistent' does not exist."):
        git_test_env.repo.get_latest_commit_sha("nonexistent")


def test_get_repo_root(git_test_env: GitTestEnv) -> None:
    """Test that we can get the repository root directory."""
    assert git_test_env.repo.get_repo_root() == git_test_env.repo_dir


def test_get_repo_root_with_no_working_tree(git_test_env: GitTestEnv) -> None:
    """Test getting repo root with no working tree."""
    # Create a bare repo
    bare_path = Path(git_test_env.temp_dir) / "bare.git"
    bare_repo = Repo.init(str(bare_path), bare=True)
    repo = GitRepo(str(bare_repo.git_dir))
    with pytest.raises(ValueError, match="does not have a working tree"):
        repo.get_repo_root()


def test_is_branch_upstream_of_another(git_test_env: GitTestEnv) -> None:
    """Test that we can check if one branch is upstream of another."""
    # Create two branches
    git_test_env.repo.create_branch("branch1")
    create_file_in_repo(git_test_env.repo_dir, "file1.txt", "content1")
    git_test_env.repo.repo.index.add(["file1.txt"])
    git_test_env.repo.repo.index.commit("Commit to branch1")

    git_test_env.repo.create_branch("branch2", "branch1")
    git_test_env.repo.switch_to_branch("branch2")
    create_file_in_repo(git_test_env.repo_dir, "file2.txt", "content2")
    git_test_env.repo.repo.index.add(["file2.txt"])
    git_test_env.repo.repo.index.commit("Commit to branch2")

    # Check if branch1 is upstream of branch2
    assert git_test_env.repo.is_branch_upstream_of_another("branch1", "branch2")
    assert not git_test_env.repo.is_branch_upstream_of_another("branch2", "branch1")


def test_is_branch_upstream_of_another_with_nonexistent_branch(
    git_test_env: GitTestEnv,
) -> None:
    """Test checking upstream status with nonexistent branch."""
    with pytest.raises(ValueError, match="does not exist"):
        git_test_env.repo.is_branch_upstream_of_another("nonexistent", "main")
    with pytest.raises(ValueError, match="does not exist"):
        git_test_env.repo.is_branch_upstream_of_another("main", "nonexistent")


def test_is_on_branch(git_test_env: GitTestEnv) -> None:
    """Test that we can check if we are on a specific branch."""
    assert git_test_env.repo.is_on_branch("main")
    git_test_env.repo.create_branch("test_branch")
    assert not git_test_env.repo.is_on_branch("test_branch")
    git_test_env.repo.switch_to_branch("test_branch")
    assert git_test_env.repo.is_on_branch("test_branch")


def test_switch_to_branch(git_test_env: GitTestEnv) -> None:
    """Test that we can switch to a branch."""
    git_test_env.repo.create_branch("test_branch")
    git_test_env.repo.switch_to_branch("test_branch")
    assert git_test_env.repo.is_on_branch("test_branch")
    git_test_env.repo.switch_to_branch("main")
    assert git_test_env.repo.is_on_branch("main")


def test_switch_to_nonexistent_branch(git_test_env: GitTestEnv) -> None:
    """Test switching to a nonexistent branch."""
    with pytest.raises(GitCommandError):
        git_test_env.repo.switch_to_branch("nonexistent")


def test_get_branch_name_from_ref_string(git_test_env: GitTestEnv) -> None:
    """Test that we can get the branch name from a ref string."""
    git_test_env.repo.create_branch("test_branch")
    branch_name = git_test_env.repo.branch_ops._get_branch_name_from_ref_string(
        "refs/heads/test_branch"
    )
    assert branch_name == "test_branch"


def test_get_branch_name_from_invalid_ref_string(git_test_env: GitTestEnv) -> None:
    """Test getting branch name from an invalid ref string."""
    branch_name = git_test_env.repo.branch_ops._get_branch_name_from_ref_string(
        "invalid/ref/string"
    )
    assert branch_name == "invalid/ref/string"
