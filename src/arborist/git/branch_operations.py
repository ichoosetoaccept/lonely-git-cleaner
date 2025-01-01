"""Branch operations module."""

from typing import Optional

from git import GitCommandError, Repo
from git.refs import Head

from arborist.exceptions import GitError
from arborist.git.common import (
    BranchName,
    get_branch,
    log_git_error,
    validate_branch_exists,
    validate_branch_name,
)


class BranchOperations:
    """Branch operations class."""

    def __init__(self, repo: Repo) -> None:
        """Initialize branch operations.

        Parameters
        ----------
        repo : Repo
            GitPython repository instance
        """
        self.repo = repo

    # Validation methods
    def _validate_not_current_branch(self, branch: Head) -> None:
        """Validate that a branch is not the current branch.

        Parameters
        ----------
        branch : Head
            Branch to validate

        Raises
        ------
        GitError
            If the branch is the current branch
        """
        if branch == self.repo.active_branch:
            raise GitError(f"Cannot delete current branch '{branch.name}'")

    def _validate_not_protected(
        self, branch: Head, protected_branches: list[str]
    ) -> None:
        """Validate that a branch is not protected.

        Parameters
        ----------
        branch : Head
            Branch to validate
        protected_branches : list[str]
            List of protected branch names

        Raises
        ------
        GitError
            If the branch is protected
        """
        if branch.name in protected_branches:
            raise GitError(f"Cannot delete protected branch '{branch.name}'")

    # Branch operations
    def _handle_worktree_deletion(self, branch: Head) -> None:
        """Handle deletion of worktrees associated with a branch.

        Parameters
        ----------
        branch : Head
            Branch to handle worktrees for

        Raises
        ------
        GitError
            If worktree deletion fails
        """
        try:
            for worktree in self.repo.git.worktree("list").splitlines():
                if branch.name in worktree:
                    path = worktree.split()[0]
                    self.repo.git.worktree("remove", "--force", path)
        except GitCommandError as err:
            log_git_error(
                GitError(str(err)),
                f"Failed to delete worktree for branch '{branch.name}'",
            )
            raise GitError(f"Failed to delete worktree: {err}") from err

    def _delete_branch_safely(self, branch: Head, force: bool = False) -> None:
        """Delete a branch safely.

        Parameters
        ----------
        branch : Head
            Branch to delete
        force : bool
            Force deletion

        Raises
        ------
        GitError
            If branch deletion fails
        """
        try:
            # Delete local branch
            self.repo.delete_head(branch.name, force=force)

            # Delete remote branch if it exists
            if branch.tracking_branch():
                remote = branch.tracking_branch().remote_name
                self.repo.git.push(remote, "--delete", branch.name)
        except GitCommandError as err:
            log_git_error(
                GitError(str(err)), f"Failed to delete branch '{branch.name}'"
            )
            raise GitError(f"Failed to delete branch: {err}") from err

    def delete_branch(
        self,
        branch_name: BranchName,
        protected_branches: Optional[list[str]] = None,
        force: bool = False,
    ) -> None:
        """Delete a branch.

        Parameters
        ----------
        branch_name : str
            Name of the branch to delete
        protected_branches : Optional[list[str]]
            List of protected branch names
        force : bool
            Force deletion

        Raises
        ------
        GitError
            If branch deletion fails
        """
        try:
            # Validate branch name and existence
            validate_branch_name(branch_name)
            validate_branch_exists(self.repo, branch_name)

            # Get branch and validate it
            branch = get_branch(self.repo, branch_name)
            self._validate_not_current_branch(branch)
            if protected_branches:
                self._validate_not_protected(branch, protected_branches)

            # Handle worktrees and delete branch
            self._handle_worktree_deletion(branch)
            self._delete_branch_safely(branch, force)
        except GitError as err:
            log_git_error(err, f"Failed to delete branch '{branch_name}'")
            raise GitError(f"Failed to delete branch: {err}") from err

    def create_branch(
        self, branch_name: BranchName, start_point: Optional[str] = None
    ) -> None:
        """Create a new branch.

        Parameters
        ----------
        branch_name : str
            Name of the branch to create
        start_point : Optional[str]
            Starting point for the branch

        Raises
        ------
        GitError
            If branch creation fails
        """
        try:
            # Validate branch name
            validate_branch_name(branch_name)

            # Create branch
            if start_point:
                validate_branch_exists(self.repo, start_point)
                self.repo.create_head(branch_name, start_point)
            else:
                self.repo.create_head(branch_name)
        except GitCommandError as err:
            log_git_error(
                GitError(str(err)), f"Failed to create branch '{branch_name}'"
            )
            raise GitError(f"Failed to create branch: {err}") from err
        except GitError as err:
            log_git_error(err, f"Failed to create branch '{branch_name}'")
            raise GitError(f"Failed to create branch: {err}") from err

    def switch_branch(self, branch_name: BranchName) -> None:
        """Switch to a branch.

        Parameters
        ----------
        branch_name : str
            Name of the branch to switch to

        Raises
        ------
        GitError
            If branch switch fails
        """
        try:
            # Validate branch name and existence
            validate_branch_name(branch_name)
            validate_branch_exists(self.repo, branch_name)

            # Switch branch
            branch = get_branch(self.repo, branch_name)
            branch.checkout()
        except GitCommandError as err:
            log_git_error(
                GitError(str(err)), f"Failed to switch to branch '{branch_name}'"
            )
            raise GitError(f"Failed to switch to branch: {err}") from err
        except GitError as err:
            log_git_error(err, f"Failed to switch to branch '{branch_name}'")
            raise GitError(f"Failed to switch to branch: {err}") from err
