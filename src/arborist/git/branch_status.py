"""Branch status management."""

from typing import Optional

from git import GitCommandError, Remote, Repo
from git.refs import Head, RemoteReference

from arborist.exceptions import GitError
from arborist.git.common import (
    BranchDict,
    BranchList,
    BranchName,
    BranchStatus,
    get_branch,
    log_git_error,
    validate_branch_exists,
    validate_branch_name,
)


class BranchStatusManager:
    """Branch status manager."""

    def __init__(self, repo: Repo) -> None:
        """Initialize branch status manager.

        Parameters
        ----------
        repo : Repo
            GitPython repository instance
        """
        self.repo = repo

    # Remote tracking methods
    def _get_tracking_branch(self, branch: Head) -> Optional[RemoteReference]:
        """Get the remote tracking branch for a local branch.

        Parameters
        ----------
        branch : Head
            The local branch

        Returns
        -------
        Optional[RemoteReference]
            The remote tracking branch, or None if not found
        """
        try:
            return branch.tracking_branch()
        except (GitCommandError, AttributeError):
            return None

    def _try_fetch_remote_branch(self, remote: Remote, branch_name: BranchName) -> bool:
        """Try to fetch a specific branch from a remote.

        Parameters
        ----------
        remote : Remote
            The remote to fetch from
        branch_name : str
            The name of the branch to fetch

        Returns
        -------
        bool
            True if the branch exists on the remote, False otherwise
        """
        try:
            remote.fetch(refspec=branch_name)
            return True
        except GitCommandError:
            return False

    def _is_branch_gone(self, branch: Head) -> bool:
        """Check if a branch is gone.

        Parameters
        ----------
        branch : Head
            Branch to check

        Returns
        -------
        bool
            True if the branch is gone, False otherwise
        """
        tracking_branch = self._get_tracking_branch(branch)
        if not tracking_branch:
            return False

        # Try to fetch from each remote until we find the branch
        for remote in self.repo.remotes:
            if self._try_fetch_remote_branch(remote, tracking_branch.remote_head):
                return False

        return True

    # Branch status methods
    def _check_branch_merged(self, branch: Head, target: Head) -> bool:
        """Check if a branch is merged into target.

        Parameters
        ----------
        branch : Head
            Branch to check
        target : Head
            Target branch to check against

        Returns
        -------
        bool
            True if branch is merged into target
        """
        try:
            # Get the merge base (common ancestor) of the two branches
            merge_base = self.repo.merge_base(branch.commit, target.commit)
            if not merge_base:
                return False

            # A branch is merged if its tip is an ancestor of the target branch
            # AND the merge base is the same as the branch tip
            return self.repo.is_ancestor(branch.commit, target.commit) and merge_base[0] == branch.commit
        except GitCommandError:
            return False

    def _get_branch_status(self, branch: Head, target_branch: BranchName = "main") -> BranchStatus:
        """Get status of a branch.

        Parameters
        ----------
        branch : Head
            Branch to check
        target_branch : str
            Branch to check for merges against

        Returns
        -------
        BranchStatus
            Status of the branch
        """
        try:
            # Check if branch is gone
            if self._is_branch_gone(branch):
                return BranchStatus.GONE

            # Check if branch is merged
            target = get_branch(self.repo, target_branch)
            if self._check_branch_merged(branch, target):
                return BranchStatus.MERGED

            return BranchStatus.UNMERGED
        except (GitCommandError, GitError) as err:
            log_git_error(GitError(str(err)), f"Failed to get status for branch '{branch.name}'")
            return BranchStatus.UNKNOWN

    # Public query methods
    def get_branch_status(self, target_branch: BranchName = "main") -> BranchDict:
        """Get status of all branches.

        Parameters
        ----------
        target_branch : str
            Branch to check for merges against

        Returns
        -------
        Dict[str, BranchStatus]
            Dictionary mapping branch names to their status

        Raises
        ------
        GitError
            If the target branch does not exist
        """
        try:
            validate_branch_name(target_branch)
            validate_branch_exists(self.repo, target_branch)
            status = {}
            for branch in self.repo.heads:
                status[branch.name] = self._get_branch_status(branch, target_branch)
            return status
        except GitError as err:
            log_git_error(err, f"Failed to get branch status for target '{target_branch}'")
            raise GitError(f"Failed to get branch status: {err}") from err

    def get_gone_branches(self) -> BranchList:
        """Get gone branches.

        Returns
        -------
        List[str]
            List of gone branch names
        """
        try:
            branch_status = self.get_branch_status()
            return [branch for branch, status in branch_status.items() if status == BranchStatus.GONE]
        except GitError as err:
            log_git_error(err, "Failed to get gone branches")
            raise GitError("Failed to get gone branches") from err

    def get_merged_branches(self, target_branch: BranchName = "main") -> BranchList:
        """Get merged branches.

        Parameters
        ----------
        target_branch : str
            Branch to check for merges against

        Returns
        -------
        List[str]
            List of merged branch names

        Raises
        ------
        GitError
            If the target branch does not exist
        """
        try:
            branch_status = self.get_branch_status(target_branch)
            return [branch for branch, status in branch_status.items() if status == BranchStatus.MERGED]
        except GitError as err:
            log_git_error(err, f"Failed to get merged branches for target '{target_branch}'")
            raise GitError(f"Failed to get merged branches: {err}") from err
