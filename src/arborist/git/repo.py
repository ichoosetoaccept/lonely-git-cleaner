"""Git repository operations."""

from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from arborist.exceptions import GitError
from arborist.git.branch_cleanup import BranchCleanup
from arborist.git.branch_operations import BranchOperations
from arborist.git.branch_status import BranchStatus, BranchStatusManager


class GitRepo:
    """Git repository operations."""

    def __init__(self, path: str | Path | None = None) -> None:
        """Initialize the repository.

        Parameters
        ----------
        path : Optional[str | Path]
            Path to the repository. If None, uses the current directory.

        Raises
        ------
        GitError
            If the repository cannot be found or is invalid.
        """
        try:
            self.repo = Repo(path or ".", search_parent_directories=True)
            self.branch_status = BranchStatusManager(self.repo)
            self.branch_ops = BranchOperations(self.repo)
            self.branch_cleanup = BranchCleanup(self.repo)
        except (InvalidGitRepositoryError, NoSuchPathError) as err:
            raise GitError("Not a git repository") from err

    def get_branch_status(self) -> dict[str, BranchStatus]:
        """Get the status of all local branches.

        Returns
        -------
        Dict[str, BranchStatus]
            A dictionary mapping branch names to their status.
        """
        return self.branch_status.get_branch_status()

    def get_merged_branches(self) -> list[str]:
        """Get all merged branches.

        Returns
        -------
        List[str]
            List of merged branch names.
        """
        return self.branch_status.get_merged_branches()

    def get_gone_branches(self) -> list[str]:
        """Get all branches whose remotes are gone.

        Returns
        -------
        List[str]
            List of branch names with gone remotes.
        """
        return self.branch_status.get_gone_branches()

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
        self.branch_ops.delete_branch(branch_name, force)

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
        self.branch_ops.delete_remote_branch(branch_name)

    def create_branch(self, branch_name: str, start_point: str | None = None) -> None:
        """Create a new branch from the given start point, or HEAD if not specified.

        Parameters
        ----------
        branch_name : str
            The name of the new branch
        start_point : Optional[str]
            The commit or branch to start from
        """
        self.branch_ops.create_branch(branch_name, start_point)

    def get_current_branch_name(self) -> str:
        """Get the name of the currently checked out branch.

        Returns
        -------
        str
            The name of the current branch
        """
        return self.branch_ops.get_current_branch_name()

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
        return self.branch_ops.get_latest_commit_sha(branch_name)

    def get_repo_root(self) -> str:
        """Get the root directory of the repository.

        Returns
        -------
        str
            The repository root directory path

        Raises
        ------
        ValueError
            If the repository does not have a working tree directory
        """
        if self.repo.working_tree_dir is None:
            raise ValueError("Repository does not have a working tree directory")
        return str(self.repo.working_tree_dir)

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
        return self.branch_ops.is_branch_upstream_of_another(
            upstream_branch_name, downstream_branch_name
        )

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
        return self.branch_ops.is_on_branch(branch_name)

    def switch_to_branch(self, branch_name: str) -> None:
        """Switch to the specified branch.

        Parameters
        ----------
        branch_name : str
            The name of the branch to switch to
        """
        self.branch_ops.switch_to_branch(branch_name)

    @property
    def heads(self):
        """Get repository heads (branches).

        Returns
        -------
        git.refs.head.Head
            The repository heads
        """
        return self.repo.heads

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
        protect : Optional[List[str]]
            List of branch patterns to protect from deletion
        force : bool
            Whether to force deletion of unmerged branches
        no_interactive : bool
            Whether to skip confirmation prompts
        dry_run : bool
            Whether to only show what would be done
        """
        self.branch_cleanup.clean(protect, force, no_interactive, dry_run)
