"""Git test environment for arborist tests."""

import os
import shutil
import tempfile
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from arborist.exceptions import GitError
from arborist.git.repo import GitRepo


def create_file_in_repo(repo_dir: str | Path, filename: str, content: str) -> None:
    """Create a file in the repository.

    Parameters
    ----------
    repo_dir : str | Path
        Path to the repository
    filename : str
        Name of the file to create
    content : str
        Content to write to the file
    """
    repo_path = Path(repo_dir)
    file_path = repo_path / filename
    with open(file_path, "w") as f:
        f.write(content)
        f.write(content)


class GitTestEnv:
    """Test environment for git operations."""

    def __init__(self, temp_dir: Path | None = None):
        """Initialize test environment.

        Parameters
        ----------
        temp_dir : Path | None
            Path to use as temporary directory. If None, a new temporary directory
            will be created.
        """
        self.temp_dir = str(temp_dir) if temp_dir else tempfile.mkdtemp()
        self.origin_dir = os.path.join(self.temp_dir, "origin")
        self.clone_dir = os.path.join(self.temp_dir, "clone")
        self.repo_dir = self.clone_dir  # For compatibility with tests

        # Initialize origin repo
        self.origin = Repo.init(self.origin_dir, bare=True)

        # Clone the repo
        raw_repo = Repo.clone_from(self.origin_dir, self.clone_dir)

        # Configure git
        raw_repo.git.config("user.name", "Test User")
        raw_repo.git.config("user.email", "test@example.com")

        # Create initial commit on main branch
        raw_repo.git.checkout("-b", "main")
        raw_repo.git.config("init.defaultBranch", "main")

        # Create GitRepo instance
        self.repo = GitRepo(self.clone_dir)

        # Create initial commit
        self.create_commit("Initial commit")
        raw_repo.git.push("origin", "main")

    def cleanup(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def create_branch(self, name: str, checkout: bool = True):
        """Create a new branch.

        Parameters
        ----------
        name : str
            Name of the branch
        checkout : bool
            Whether to check out the branch after creation

        """
        try:
            self.repo.create_branch(name)
            if checkout:
                self.repo.switch_to_branch(name)
            else:
                self.repo.switch_to_branch("main")
        except GitError as err:
            raise GitError(f"Failed to create branch {name}: {err}") from err

    def checkout_branch(self, name: str):
        """Check out a branch.

        Parameters
        ----------
        name : str
            Name of the branch

        """
        try:
            self.repo.switch_to_branch(name)
        except GitError as err:
            raise GitError(f"Failed to check out branch {name}: {err}") from err

    def create_commit(self, message: str = "test commit"):
        """Create a commit.

        Parameters
        ----------
        message : str
            Commit message

        """
        try:
            # Create a file with random content
            file_path = os.path.join(self.clone_dir, f"{os.urandom(8).hex()}.txt")
            with open(file_path, "w") as f:
                f.write("test content")

            # Get the raw repo for low-level operations
            raw_repo = self.repo.repo
            raw_repo.index.add([file_path])
            raw_repo.index.commit(message)
        except (GitCommandError, GitError) as err:
            raise GitError(f"Failed to create commit: {err}") from err

    def merge_branch(self, source: str, target: str = "main"):
        """Merge a branch.

        Parameters
        ----------
        source : str
            Name of the source branch
        target : str
            Name of the target branch

        """
        try:
            current = self.repo.get_current_branch_name()
            self.repo.switch_to_branch(target)
            # Use raw repo for merge since GitRepo doesn't have merge method
            self.repo.repo.git.merge(source)
            if current != target:
                self.repo.switch_to_branch(current)
        except (GitCommandError, GitError) as err:
            raise GitError(
                f"Failed to merge branch {source} into {target}: {err}"
            ) from err

    def push_branch(self, name: str):
        """Push a branch to origin.

        Parameters
        ----------
        name : str
            Name of the branch

        """
        try:
            # Use raw repo for push since GitRepo doesn't have push method
            self.repo.repo.git.push("origin", name)
        except GitCommandError as err:
            raise GitError(f"Failed to push branch {name}: {err}") from err

    def delete_remote_branch(self, name: str):
        """Delete a remote branch.

        Parameters
        ----------
        name : str
            Name of the branch

        """
        try:
            self.repo.delete_remote_branch(name)
        except GitError as err:
            raise GitError(f"Failed to delete remote branch {name}: {err}") from err

    def run_git(self, *args: str) -> str:
        """Run a git command.

        Parameters
        ----------
        *args : str
            Command arguments

        Returns
        -------
        str
            Command output

        """
        try:
            # Use raw repo for direct git commands
            cmd = ["git", *args]
            output = self.repo.repo.git.execute(cmd)
            return str(output) if output is not None else ""
        except GitCommandError as err:
            raise GitError(f"Failed to run git command: {err}") from err
