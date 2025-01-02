"""Branch operations."""

from typing import List, Optional, Set

from git import GitCommandError, Head, Remote
from git.repo.base import Repo as GitRepo

from arborist.errors import GitError
from arborist.git.common import (
    BranchName,
    get_branch,
    get_current_branch_name,
    is_branch_upstream_of_another,
    validate_branch_exists,
    validate_branch_name,
)


class BranchOperations:
    """Branch operations."""

    def __init__(self, repo: GitRepo) -> None:
        """Initialize branch operations.

        Parameters
        ----------
        repo : GitRepo
            Git repository
        """
        self.repo = repo

    def _validate_not_current_branch(self, branch: Head) -> None:
        """Validate that a branch is not the current branch.

        Parameters
        ----------
        branch : Head
            Branch to validate

        Raises
        ------
        GitError
            If branch is the current branch
        """
        if branch == self.repo.active_branch:
            raise GitError(f"Cannot delete current branch '{branch.name}'")

    def _validate_not_protected(self, branch: Head, protected_branches: List[str]) -> None:
        """Validate that a branch is not protected.

        Parameters
        ----------
        branch : Head
            Branch to validate
        protected_branches : List[str]
            List of protected branch names

        Raises
        ------
        GitError
            If branch is protected
        """
        # First check for exact matches
        if branch.name in protected_branches:
            raise GitError(f"Cannot delete protected branch '{branch.name}'")

        # Then check for pattern matches
        for pattern in protected_branches:
            # Handle wildcard patterns
            if "*" in pattern:
                import fnmatch

                if fnmatch.fnmatch(branch.name, pattern):
                    raise GitError(f"Cannot delete protected branch '{branch.name}'")
            # Handle prefix matches (e.g. 'main' should protect 'main' and 'main-1.0')
            elif branch.name.startswith(pattern + "-") or branch.name == pattern:
                raise GitError(f"Cannot delete protected branch '{branch.name}'")

    def _delete_branch_safely(self, branch: Head, force: bool = False) -> None:
        """Delete a branch safely.

        Parameters
        ----------
        branch : Head
            Branch to delete
        force : bool, optional
            Force deletion even if branch is not merged, by default False

        Raises
        ------
        GitError
            If branch deletion fails
        """
        try:
            # Validate not current branch
            self._validate_not_current_branch(branch)

            # Delete remote branch first if it exists
            tracking_branch = branch.tracking_branch()
            if tracking_branch:
                remote = tracking_branch.remote_name
                try:
                    self.repo.git.push(remote, "--delete", branch.name)
                    # Fetch to update remote refs
                    self.repo.git.fetch(remote, "--prune")
                except GitCommandError as err:
                    raise GitError(f"Failed to delete remote branch: {err}") from err

            # Delete local branch
            self.repo.delete_head(branch.name, force=force)
        except GitCommandError as err:
            raise GitError(f"Failed to delete branch: {err}") from err

    def delete_branch(
        self,
        branch_name: BranchName,
        force: bool = False,
        no_verify: bool = False,
        protected_branches: Optional[List[str]] = None,
    ) -> None:
        """Delete a branch.

        Parameters
        ----------
        branch_name : BranchName
            Name of the branch to delete
        force : bool, optional
            Force deletion even if branch is not merged, by default False
        no_verify : bool, optional
            Skip verification checks, by default False
        protected_branches : Optional[List[str]], optional
            List of protected branch names, by default None

        Raises
        ------
        GitError
            If branch deletion fails
        """
        # Validate branch name
        validate_branch_name(branch_name)
        validate_branch_exists(self.repo, branch_name)

        # Get branch
        branch = get_branch(self.repo, branch_name)

        # Verify branch can be deleted
        if not no_verify:
            self._validate_not_current_branch(branch)
            if protected_branches:
                self._validate_not_protected(branch, protected_branches)
            if not force and not self._is_branch_merged(branch):
                raise GitError(f"Branch '{branch.name}' is not fully merged")

        try:
            # Delete branch
            self._delete_branch_safely(branch, force)
        except GitCommandError as err:
            raise GitError(f"Failed to delete branch: {err}") from err

    def _is_branch_merged(self, branch: Head) -> bool:
        """Check if a branch is merged.

        Parameters
        ----------
        branch : Head
            Branch to check

        Returns
        -------
        bool
            True if branch is merged, False otherwise
        """
        # Check if branch is merged into any other branch
        for other_branch in self.repo.heads:
            if other_branch != branch and is_branch_upstream_of_another(
                self.repo,
                branch.name,
                other_branch.name,
            ):
                return True

        return False

    def get_merged_branches(self, remote: Optional[Remote] = None) -> List[BranchName]:
        """Get list of merged branches.

        Parameters
        ----------
        remote : Optional[Remote], optional
            Remote to check branches against, by default None

        Returns
        -------
        List[BranchName]
            List of merged branch names
        """
        merged_branches = []
        for branch in self.repo.heads:
            if self._is_branch_merged(branch):
                merged_branches.append(branch.name)

        return merged_branches

    def get_gone_branches(self) -> List[BranchName]:
        """Get list of branches whose upstream is gone.

        Returns
        -------
        List[BranchName]
            List of branch names
        """
        gone_branches = []
        for branch in self.repo.heads:
            tracking_branch = branch.tracking_branch()
            if tracking_branch is None:
                continue
            if not tracking_branch.is_valid():
                gone_branches.append(branch.name)

        return gone_branches

    def clean(
        self,
        force: bool = False,
        no_verify: bool = False,
        dry_run: bool = False,
        no_interactive: bool = False,
        protect: Optional[Set[str]] = None,
    ) -> None:
        """Clean up branches.

        Parameters
        ----------
        force : bool, optional
            Force deletion even if branch is not merged, by default False
        no_verify : bool, optional
            Skip verification checks, by default False
        dry_run : bool, optional
            Only show what would be done, by default False
        no_interactive : bool, optional
            Do not ask for confirmation, by default False
        protect : Optional[Set[str]], optional
            Set of branch patterns to protect, by default None
        """
        # Get list of branches to delete
        to_delete = set()
        to_delete.update(self.get_merged_branches())
        to_delete.update(self.get_gone_branches())

        # Remove protected branches
        if protect:
            to_delete = {b for b in to_delete if not any(p in b for p in protect)}

        # Remove current branch
        current_branch = get_current_branch_name(self.repo)
        if current_branch in to_delete:
            to_delete.remove(current_branch)

        if not to_delete:
            return

        # Print branches to delete
        print("Branches to delete:")
        for branch in sorted(to_delete):
            print(f"  {branch}")

        if dry_run:
            return

        # Ask for confirmation
        if not no_interactive:
            for branch in sorted(to_delete):
                answer = input(f"Delete branch '{branch}'? [y/N] ")
                if answer.lower() != "y":
                    continue
                self.delete_branch(branch, force=force, no_verify=no_verify)
        else:
            for branch in sorted(to_delete):
                self.delete_branch(branch, force=force, no_verify=no_verify)
