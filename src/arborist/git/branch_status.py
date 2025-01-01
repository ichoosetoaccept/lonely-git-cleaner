"""Branch status management."""

from enum import Enum, auto

from git import GitCommandError, Repo
from git.refs import Head, RemoteReference


class BranchStatus(Enum):
    """Branch status enum."""

    MERGED = auto()
    UNMERGED = auto()
    GONE = auto()
    UNKNOWN = auto()


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

    def _get_branch_status(
        self, branch: Head, target_branch: str = "main"
    ) -> BranchStatus:
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
            target = self.repo.heads[target_branch]
            if self.repo.is_ancestor(branch.commit, target.commit):
                return BranchStatus.MERGED

            return BranchStatus.UNMERGED
        except (GitCommandError, KeyError):
            return BranchStatus.UNKNOWN

    def get_branch_status(self, target_branch: str = "main") -> dict[str, BranchStatus]:
        """Get status of all branches.

        Parameters
        ----------
        target_branch : str
            Branch to check for merges against

        Returns
        -------
        Dict[str, BranchStatus]
            Dictionary mapping branch names to their status
        """
        status = {}
        for branch in self.repo.heads:
            status[branch.name] = self._get_branch_status(branch, target_branch)
        return status

    def _get_remote_tracking_branches(self) -> dict[str, RemoteReference]:
        """Get remote tracking branches.

        Returns
        -------
        Dict[str, RemoteReference]
            Dictionary mapping local branch names to their remote tracking branches
        """
        tracking_branches = {}
        try:
            for branch in self.repo.heads:
                tracking_ref = branch.tracking_branch()
                if tracking_ref:
                    tracking_branches[branch.name] = tracking_ref
        except GitCommandError:
            pass
        return tracking_branches

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
        try:
            tracking_branch = branch.tracking_branch()
            if not tracking_branch:
                return False

            remote_exists = False
            for remote in self.repo.remotes:
                try:
                    # Try to fetch the specific branch
                    remote.fetch(refspec=tracking_branch.remote_head)
                    remote_exists = True
                    break
                except GitCommandError:
                    continue

            return not remote_exists
        except (GitCommandError, AttributeError):
            return False

    def get_gone_branches(self) -> list[str]:
        """Get gone branches.

        Returns
        -------
        List[str]
            List of gone branch names
        """
        branch_status = self.get_branch_status()
        return [
            branch
            for branch, status in branch_status.items()
            if status == BranchStatus.GONE
        ]

    def get_merged_branches(self, target_branch: str = "main") -> list[str]:
        """Get merged branches.

        Parameters
        ----------
        target_branch : str
            Branch to check for merges against

        Returns
        -------
        List[str]
            List of merged branch names
        """
        branch_status = self.get_branch_status(target_branch)
        return [
            branch
            for branch, status in branch_status.items()
            if status == BranchStatus.MERGED
        ]
