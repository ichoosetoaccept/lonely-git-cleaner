"""Test environment for Git operations."""

import shutil
import tempfile
from pathlib import Path

from arborist import git


class GitHubTestEnvironment:
    """Test environment for Git operations."""

    def __init__(self):
        """Initialize test environment."""
        self.repo_dir = Path(tempfile.mkdtemp())
        self.remote_dir = None

    def setup(self):
        """Set up the test environment."""
        # Create directories
        self.repo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize repository
        self._init_repo()

        # Create initial commit
        self.commit_file("README.md", "# Test Repository")

        # Push to remote
        self._run_git("push", "-u", "origin", "main")

    def _init_repo(self):
        """Initialize a Git repository."""
        # Initialize main repo
        self._run_git("init", "-b", "main")

        # Configure user info for commits
        self._run_git("config", "user.name", "Test User")
        self._run_git("config", "user.email", "test@example.com")

        # Create bare repo to act as remote
        self.remote_dir = Path(tempfile.mkdtemp())
        git.run_git_command(["init", "--bare"], cwd=self.remote_dir)

        # Add remote
        self._run_git("remote", "add", "origin", str(self.remote_dir))

    def create_branch(self, branch_name: str, message: str):
        """Create a new branch and commit a file to it.

        Parameters
        ----------
        branch_name : str
            Name of the branch to create.
        message : str
            Commit message.

        """
        # Create and switch to new branch
        self._run_git("checkout", "-b", branch_name)

        # Create and commit a file
        filename = f"{branch_name.replace('/', '_')}.txt"
        file_path = self.repo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(message)

        # Add and commit
        self._run_git("add", filename)
        self._run_git("commit", "-m", message)

        # Push the branch to remote
        self._run_git("push", "-u", "origin", branch_name)

    def commit_file(self, filename: str, content: str, branch: str = "main") -> None:
        """Create and commit a file.

        Parameters
        ----------
        filename : str
            Name of the file to create.
        content : str
            Content to write to the file.
        branch : str, optional
            Branch to commit to, by default "main".

        """
        # Switch to or create branch
        try:
            self._run_git("checkout", branch)
        except git.GitError:
            self._run_git("checkout", "-b", branch)

        # Create and commit file
        file_path = self.repo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        self._run_git("add", filename)
        self._run_git("commit", "-m", f"Add {filename}")

    def merge_branch(self, branch: str, target: str = "main") -> None:
        """Merge a branch into another branch.

        Parameters
        ----------
        branch : str
            Branch to merge.
        target : str, optional
            Target branch to merge into, by default "main".

        """
        # Switch to target branch
        self._run_git("checkout", target)

        # Merge the branch
        self._run_git("merge", "--no-ff", branch, "-m", f"Merge {branch} into {target}")

        # Push changes
        self._run_git("push", "origin", target)

    def switch_branch(self, branch: str) -> None:
        """Switch to a branch.

        Parameters
        ----------
        branch : str
            Branch to switch to.

        """
        self._run_git("checkout", branch)

    def delete_remote_branch(self, branch: str) -> None:
        """Delete a remote branch.

        Parameters
        ----------
        branch : str
            Branch to delete.

        """
        self._run_git("push", "origin", "--delete", branch)

    def push_branch(self, branch: str) -> None:
        """Push a branch to the remote.

        Parameters
        ----------
        branch : str
            Branch to push.

        """
        self._run_git("push", "-u", "origin", branch)

    def get_branches(self) -> list[str]:
        """Get list of local branches.

        Returns
        -------
        list[str]
            List of branch names.

        """
        stdout, _ = self._run_git("branch", "--format", "%(refname:short)")
        return [branch.strip() for branch in stdout.splitlines() if branch.strip()]

    def get_remote_branches(self) -> list[str]:
        """Get list of remote branches.

        Returns
        -------
        list[str]
            List of remote branch names.

        """
        stdout, _ = git.run_git_command(
            ["branch", "-r", "--format=%(refname:short)"],
            cwd=self.repo_dir,
        )
        return [
            b.strip().replace("origin/", "") for b in stdout.splitlines() if b.strip()
        ]

    def cleanup(self):
        """Clean up test environment."""
        shutil.rmtree(self.repo_dir)
        shutil.rmtree(self.remote_dir)

    def _run_git(self, *args: str) -> tuple[str, str]:
        """Run a Git command in the test repository.

        Parameters
        ----------
        *args : str
            Command arguments to pass to Git.

        Returns
        -------
        tuple[str, str]
            A tuple of (stdout, stderr) from the command.

        """
        return git.run_git_command(list(args), cwd=self.repo_dir)
