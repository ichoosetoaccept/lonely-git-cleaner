"""Branch manipulation operations."""

from git import Repo
from git.exc import GitCommandError

from arborist.exceptions import GitError


class BranchOperations:
    """Handles branch manipulation operations."""

    def __init__(self, repo: Repo) -> None:
        """Initialize with a Git repository.

        Parameters
        ----------
        repo : Repo
            The GitPython repository instance
        """
        self.repo = repo

    def _validate_branch(self, branch_name: str) -> None:
        """Validate that a branch exists.

        Parameters
        ----------
        branch_name : str
            The name of the branch to validate

        Raises
        ------
        GitError
            If the branch does not exist
        """
        if branch_name not in self.repo.heads:
            raise GitError(f"Branch {branch_name} does not exist")

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a local branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch to delete
        force : bool
            Whether to force deletion of unmerged branches

        Raises
        ------
        GitError
            If the branch cannot be deleted
        """
        try:
            self._validate_branch(branch_name)

            # First check if we're on the branch we're trying to delete
            current_branch = self.repo.active_branch.name
            if current_branch == branch_name:
                raise GitError("Cannot delete current branch")

            # Try to delete the branch
            try:
                delete_flag = "-D" if force else "-d"
                self.repo.git.branch(delete_flag, branch_name)
            except GitCommandError as err:
                if "used by worktree" in str(err):
                    # Remove worktree first
                    try:
                        self.repo.git.worktree("remove", "--force", branch_name)
                        self.repo.git.branch(delete_flag, branch_name)
                    except GitCommandError as worktree_err:
                        raise GitError(
                            f"Failed to remove worktree: {worktree_err}"
                        ) from worktree_err
                elif "not fully merged" in str(err) and not force:
                    raise GitError(
                        f"Branch {branch_name} is not fully merged. "
                        "Use --force to delete anyway."
                    ) from err
                else:
                    raise GitError(
                        f"Failed to delete branch {branch_name}: {err}"
                    ) from err

        except GitError as err:
            raise GitError(f"Failed to delete branch {branch_name}: {err}") from err

    def delete_remote_branch(self, branch_name: str) -> None:
        """Delete a remote branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch to delete

        Raises
        ------
        GitError
            If the branch cannot be deleted
        """
        try:
            # Check if remote exists
            if not self.repo.remotes:
                raise GitError("No remote repository")

            # Delete the branch
            try:
                self.repo.git.push("origin", "--delete", branch_name)
            except GitCommandError as err:
                msg = f"Failed to delete remote branch {branch_name}: {err}"
                raise GitError(msg) from err

        except GitError as err:
            msg = f"Failed to delete remote branch {branch_name}: {err}"
            raise GitError(msg) from err

    def create_branch(self, branch_name: str, start_point: str | None = None) -> None:
        """Create a new branch from the given start point, or HEAD if not specified.

        Parameters
        ----------
        branch_name : str
            The name of the new branch
        start_point : Optional[str]
            The commit or branch to start from
        """
        if start_point:
            self.repo.git.branch(branch_name, start_point)
        else:
            self.repo.create_head(branch_name)

    def get_current_branch_name(self) -> str:
        """Get the name of the currently checked out branch.

        Returns
        -------
        str
            The name of the current branch
        """
        return self.repo.active_branch.name

    def get_latest_commit_sha(self, branch_name: str) -> str:
        """Get the latest commit SHA for the given branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch

        Returns
        -------
        str
            The commit SHA

        Raises
        ------
        ValueError
            If the branch does not exist
        """
        try:
            return self.repo.branches[branch_name].commit.hexsha
        except IndexError as err:
            raise ValueError(f"Branch '{branch_name}' does not exist.") from err

    def is_branch_upstream_of_another(
        self, upstream_branch_name: str, downstream_branch_name: str
    ) -> bool:
        """Check if one branch is upstream of another.

        Parameters
        ----------
        upstream_branch_name : str
            The name of the potential upstream branch
        downstream_branch_name : str
            The name of the potential downstream branch

        Returns
        -------
        bool
            True if upstream_branch is an ancestor of downstream_branch
        """
        try:
            upstream_sha = self.get_latest_commit_sha(upstream_branch_name)
            downstream_sha = self.get_latest_commit_sha(downstream_branch_name)
            self.repo.git.merge_base("--is-ancestor", upstream_sha, downstream_sha)
            return True
        except GitCommandError:
            return False

    def is_on_branch(self, branch_name: str) -> bool:
        """Check if the current branch is the specified branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch to check

        Returns
        -------
        bool
            True if the current branch matches the specified branch
        """
        return self.get_current_branch_name() == branch_name

    def switch_to_branch(self, branch_name: str) -> None:
        """Switch to the specified branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch to switch to
        """
        self.repo.git.checkout(branch_name)

    def _get_branch_name_from_ref_string(self, ref_string: str) -> str:
        """Get branch name from a ref string.

        Parameters
        ----------
        ref_string : str
            The ref string (e.g., 'refs/heads/main')

        Returns
        -------
        str
            The branch name
        """
        if ref_string.startswith("refs/heads/"):
            return ref_string[len("refs/heads/") :]
        return ref_string
