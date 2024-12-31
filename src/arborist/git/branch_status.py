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
            GitPython repository object

        """
        self.repo = repo

    def _get_merged_branches(self, target_branch: str = "main") -> set[str]:
        """Get merged branches.

        Parameters
        ----------
        target_branch : str, optional
            Branch to check for merges against, by default "main"

        Returns
        -------
        Set[str]
            Set of merged branch names

        """
        try:
            merged_branches = set()
            for branch in self.repo.heads:
                if branch.name == target_branch:
                    continue
                try:
                    merge_base = self.repo.merge_base(branch, target_branch)
                    if merge_base and merge_base[0] == branch.commit:
                        merged_branches.add(branch.name)
                except GitCommandError:
                    continue
            return merged_branches
        except GitCommandError:
            return set()

    def _get_gone_branches_from_status(self) -> set[str]:
        """Get gone branches from git status.

        Returns
        -------
        Set[str]
            Set of gone branch names

        """
        try:
            gone_branches = set()
            status = self.repo.git.status("-sb")
            for line in status.split("\n"):
                if "[gone]" in line:
                    branch = line.split("...")[0].strip("# ")
                    gone_branches.add(branch)
            return gone_branches
        except GitCommandError:
            return set()

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
                    remote.fetch(tracking_branch.remote_head)
                    remote_exists = True
                    break
                except GitCommandError:
                    continue

            return not remote_exists
        except (GitCommandError, AttributeError):
            return False

    def get_branch_status(self, target_branch: str = "main") -> dict[str, BranchStatus]:
        """Get branch status.

        Parameters
        ----------
        target_branch : str, optional
            Branch to check for merges against, by default "main"

        Returns
        -------
        Dict[str, BranchStatus]
            Dictionary mapping branch names to their status

        """
        try:
            # Fetch from all remotes to ensure we have up-to-date information
            for remote in self.repo.remotes:
                try:
                    remote.fetch()
                except GitCommandError:
                    pass

            branch_status = {}
            merged_branches = self._get_merged_branches(target_branch)
            gone_branches = self._get_gone_branches_from_status()

            for branch in self.repo.heads:
                if branch.name == target_branch:
                    continue

                try:
                    if branch.name in gone_branches or self._is_branch_gone(branch):
                        branch_status[branch.name] = BranchStatus.GONE
                    elif branch.name in merged_branches:
                        branch_status[branch.name] = BranchStatus.MERGED
                    else:
                        branch_status[branch.name] = BranchStatus.UNMERGED
                except (GitCommandError, AttributeError):
                    branch_status[branch.name] = BranchStatus.UNKNOWN

            return branch_status
        except GitCommandError:
            return {
                branch.name: BranchStatus.UNKNOWN
                for branch in self.repo.heads
                if branch.name != target_branch
            }

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
        target_branch : str, optional
            Branch to check for merges against, by default "main"

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
