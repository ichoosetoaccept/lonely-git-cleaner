"""Branch cleanup operations."""

from git import GitCommandError, Repo
from rich import print

from arborist.exceptions import GitError
from arborist.git.branch_status import BranchStatus, BranchStatusManager


class BranchCleanup:
    """Branch cleanup operations."""

    def __init__(self, repo: Repo) -> None:
        """Initialize branch cleanup.

        Parameters
        ----------
        repo : Repo
            GitPython repository object
        """
        self.repo = repo
        self.status_manager = BranchStatusManager(repo)

    def _is_protected_by_pattern(self, branch: str, patterns: list[str]) -> bool:
        """Check if a branch is protected by any pattern.

        Parameters
        ----------
        branch : str
            Branch name to check
        patterns : List[str]
            List of patterns to check against

        Returns
        -------
        bool
            True if branch is protected, False otherwise
        """
        if not patterns:
            return False
        return any(pattern in branch for pattern in patterns)

    def _get_branches_to_delete(
        self, force: bool, protect: list[str] | None = None
    ) -> list[str]:
        """Get list of branches to delete.

        Parameters
        ----------
        force : bool
            Whether to include unmerged branches
        protect : Optional[List[str]]
            List of branch patterns to protect

        Returns
        -------
        List[str]
            List of branch names to delete
        """
        status = self.status_manager.get_branch_status()
        to_delete = []

        for branch, state in status.items():
            # Skip protected branches
            if protect and self._is_protected_by_pattern(branch, protect):
                continue

            # Include branch if it's merged or gone
            if state in (BranchStatus.MERGED, BranchStatus.GONE):
                to_delete.append(branch)
            # Include unmerged branches if force is True
            elif force and state == BranchStatus.UNMERGED:
                to_delete.append(branch)

        return to_delete

    def _validate_branch_exists(self, branch: str) -> None:
        """Validate that a branch exists.

        Parameters
        ----------
        branch : str
            Branch name to validate

        Raises
        ------
        GitError
            If branch does not exist
        """
        if branch not in self.repo.heads:
            raise GitError(f"Branch '{branch}' does not exist")

    def _validate_not_current_branch(self, branch: str) -> None:
        """Validate that a branch is not the current branch.

        Parameters
        ----------
        branch : str
            Branch name to validate

        Raises
        ------
        GitError
            If branch is current branch
        """
        if self.repo.active_branch.name == branch:
            raise GitError(f"Cannot delete current branch '{branch}'")

    def _validate_branch_merged(self, branch: str) -> None:
        """Validate that a branch is merged.

        Parameters
        ----------
        branch : str
            Branch name to validate

        Raises
        ------
        GitError
            If branch is not merged
        """
        status = self.status_manager.get_branch_status()
        if status[branch] == BranchStatus.UNMERGED:
            raise GitError(f"Branch '{branch}' is not fully merged")

    def _find_safe_branch(self, current: str, to_delete: set[str]) -> str | None:
        """Find a safe branch to switch to.

        Parameters
        ----------
        current : str
            Current branch name
        to_delete : Set[str]
            Set of branches to be deleted

        Returns
        -------
        Optional[str]
            Name of safe branch to switch to, or None if current branch is not in
            to_delete
        """
        # If current branch is not in to_delete, no need to find a safe branch
        if current not in to_delete:
            return None

        # Find a branch that's not in to_delete and not the current branch
        for branch in self.repo.heads:
            if branch.name not in to_delete and branch.name != current:
                return branch.name
        return None

    def _switch_to_safe_branch(
        self, current: str, to_delete: set[str]
    ) -> tuple[bool, str]:
        """Switch to a safe branch if current branch will be deleted.

        Parameters
        ----------
        current : str
            Current branch name
        to_delete : Set[str]
            Set of branches to be deleted

        Returns
        -------
        Tuple[bool, str]
            Success flag and message
        """
        if current not in to_delete:
            return True, ""

        safe_branch = self._find_safe_branch(current, to_delete)
        if not safe_branch:
            return False, f"Cannot find a safe branch to switch to from {current}"

        try:
            self.repo.heads[safe_branch].checkout()
            return True, f"Switched to branch '{safe_branch}'"
        except GitCommandError as err:
            return False, f"Failed to switch to branch '{safe_branch}': {err}"

    def _perform_branch_deletion(self, branch: str, force: bool) -> tuple[bool, str]:
        """Perform the actual branch deletion.

        Parameters
        ----------
        branch : str
            Branch to delete
        force : bool
            Whether to force delete

        Returns
        -------
        Tuple[bool, str]
            Success flag and message
        """
        try:
            self.repo.delete_head(branch, force=force)
            return True, ""
        except GitCommandError as err:
            return False, f"Failed to delete branch '{branch}': {err}"

    def _delete_single_branch(
        self, branch: str, force: bool, status: dict[str, BranchStatus]
    ) -> tuple[bool, str | None]:
        """Delete a single branch.

        Parameters
        ----------
        branch : str
            Branch to delete
        force : bool
            Whether to force delete
        status : dict[str, BranchStatus]
            Branch status dictionary

        Returns
        -------
        Tuple[bool, Optional[str]]
            Success flag and optional error message
        """
        try:
            # Validate branch exists
            self._validate_branch_exists(branch)

            # Validate not current branch
            self._validate_not_current_branch(branch)

            # Check if branch is merged unless force is True
            if not force:
                self._validate_branch_merged(branch)

            # Perform deletion
            success, error = self._perform_branch_deletion(branch, force)
            if not success:
                return False, error

            return True, None

        except GitError as err:
            return False, str(err)

    def _prompt_for_deletion(self, to_delete: list[str]) -> bool:
        """Prompt user for deletion confirmation.

        Parameters
        ----------
        to_delete : List[str]
            List of branches to delete

        Returns
        -------
        bool
            True if user confirms, False otherwise
        """
        print("\nBranches to delete:")
        for branch in to_delete:
            print(f"  - {branch}")
        response = input("\nDelete these branches? [y/N] ")
        return response.lower() == "y"

    def _handle_dry_run(self, to_delete: list[str]) -> None:
        """Handle dry run mode.

        Parameters
        ----------
        to_delete : List[str]
            List of branches that would be deleted
        """
        if not to_delete:
            print("No branches to delete")
            return

        print("\nWould delete the following branches:")
        for branch in to_delete:
            print(f"  - {branch}")

    def _print_deletion_results(
        self, deleted: list[str], failed: list[tuple[str, str]]
    ) -> None:
        """Print the results of branch deletion.

        Parameters
        ----------
        deleted : List[str]
            List of successfully deleted branches
        failed : List[Tuple[str, str]]
            List of failed branches and their error messages
        """
        if deleted:
            print("\n[green]Deleted branches:[/green]")
            for branch in deleted:
                print(f"  - {branch}")

        if failed:
            print("\n[red]Failed to delete:[/red]")
            for branch, error in failed:
                print(f"  - {branch}: {error}")

    def _delete_branches_batch(
        self, to_delete: list[str], force: bool, status: dict[str, BranchStatus]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Delete a batch of branches.

        Parameters
        ----------
        to_delete : List[str]
            List of branches to delete
        force : bool
            Whether to force delete
        status : dict[str, BranchStatus]
            Branch status dictionary

        Returns
        -------
        Tuple[List[str], List[Tuple[str, str]]]
            Lists of deleted branches and failed branches with their error messages
        """
        deleted = []
        failed = []
        for branch in to_delete:
            success, error = self._delete_single_branch(branch, force, status)
            if success:
                deleted.append(branch)
            else:
                failed.append((branch, error))
        return deleted, failed

    def _delete_branches_in_clean(
        self,
        to_delete: list[str],
        force: bool,
        no_interactive: bool,
        dry_run: bool,
    ) -> None:
        """Delete branches in clean operation.

        Parameters
        ----------
        to_delete : List[str]
            List of branches to delete
        force : bool
            Whether to force delete
        no_interactive : bool
            Whether to skip confirmation
        dry_run : bool
            Whether to perform a dry run
        """
        if not to_delete:
            print("No branches to delete")
            return

        if dry_run:
            self._handle_dry_run(to_delete)
            return

        # Get confirmation if needed
        if not no_interactive and not self._prompt_for_deletion(to_delete):
            print("Operation cancelled")
            return

        # Switch to safe branch if needed
        current = self.repo.active_branch.name
        success, message = self._switch_to_safe_branch(current, set(to_delete))
        if not success:
            print(f"[red]Error:[/red] {message}")
            return
        if message:
            print(message)

        # Get branch status and delete branches
        status = self.status_manager.get_branch_status()
        deleted, failed = self._delete_branches_batch(to_delete, force, status)

        # Print results
        self._print_deletion_results(deleted, failed)

    def clean(
        self,
        protect: list[str] | None = None,
        force: bool = False,
        no_interactive: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Clean up merged and gone branches.

        Parameters
        ----------
        protect : Optional[List[str]], optional
            List of branch patterns to protect, by default None
        force : bool, optional
            Whether to force delete unmerged branches, by default False
        no_interactive : bool, optional
            Whether to skip confirmation prompts, by default False
        dry_run : bool, optional
            Whether to perform a dry run, by default False
        """
        to_delete = self._get_branches_to_delete(force, protect)
        self._delete_branches_in_clean(to_delete, force, no_interactive, dry_run)

    def delete_branch(self, branch: str, force: bool = False) -> None:
        """Delete a branch.

        Parameters
        ----------
        branch : str
            Branch to delete
        force : bool, optional
            Whether to force delete, by default False

        Raises
        ------
        GitError
            If branch deletion fails
        """
        status = self.status_manager.get_branch_status()
        success, error = self._delete_single_branch(branch, force, status)
        if not success:
            raise GitError(error)
