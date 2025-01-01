"""Worktree operations."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from git import GitCommandError, Repo

from arborist.errors import ErrorCode, GitError
from arborist.git.common import BranchName


@dataclass
class WorktreeInfo:
    """Information about a worktree."""

    path: Path
    branch: Optional[str]
    commit: str
    is_bare: bool
    is_detached: bool
    is_prunable: bool


class WorktreeManager:
    """Manage Git worktrees."""

    # Regular expressions for parsing worktree output
    BRANCH_PATTERN = re.compile(r"\[branch (.+?)\]")
    DETACHED_PATTERN = re.compile(r"\(HEAD detached at (.+?)\)")

    def __init__(self, repo: Repo) -> None:
        """Initialize worktree manager.

        Parameters
        ----------
        repo : Repo
            GitPython repository instance
        """
        self.repo = repo

    def _parse_worktree_line(self, line: str) -> WorktreeInfo:
        """Parse a line from git worktree list output.

        Parameters
        ----------
        line : str
            Line from git worktree list output

        Returns
        -------
        WorktreeInfo
            Parsed worktree information

        Raises
        ------
        GitError
            If the line cannot be parsed
        """
        try:
            parts = line.split()
            path = Path(parts[0])
            commit = parts[1]
            branch = None
            is_detached = True  # Default to True, set to False only if we find a branch
            is_bare = False
            is_prunable = False

            # Join the rest of the line for regex matching
            rest = " ".join(parts[2:])

            # Check for branch name in [branch name] format
            branch_match = self.BRANCH_PATTERN.search(rest)
            if branch_match:
                branch = branch_match.group(1)
                is_detached = False

            # Check for flags
            is_bare = "[bare]" in rest
            is_prunable = "[prunable]" in rest

            return WorktreeInfo(
                path=path,
                branch=branch,
                commit=commit,
                is_bare=is_bare,
                is_detached=is_detached,
                is_prunable=is_prunable,
            )
        except (IndexError, ValueError) as err:
            raise GitError(
                message="Failed to parse worktree information",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"Line: {line}",
                cause=err,
            ) from err

    def list_worktrees(self) -> List[WorktreeInfo]:
        """List all worktrees.

        Returns
        -------
        List[WorktreeInfo]
            List of worktree information

        Raises
        ------
        GitError
            If worktrees cannot be listed
        """
        try:
            output = self.repo.git.worktree("list", "--porcelain")
            worktrees = []
            current_info = {}

            for line in output.splitlines():
                if not line:
                    if current_info:
                        # Convert porcelain format to standard format for parsing
                        path = current_info.get("worktree", "")
                        commit = current_info.get("HEAD", "")
                        branch = current_info.get("branch", "")
                        if branch.startswith("refs/heads/"):
                            branch = branch[11:]  # Remove refs/heads/ prefix
                            formatted_line = f"{path} {commit} [branch {branch}]"
                        else:
                            formatted_line = f"{path} {commit}"
                        worktrees.append(self._parse_worktree_line(formatted_line))
                        current_info = {}
                    continue

                key, value = line.split(" ", 1)
                current_info[key] = value

            if current_info:
                # Handle the last worktree info
                path = current_info.get("worktree", "")
                commit = current_info.get("HEAD", "")
                branch = current_info.get("branch", "")
                if branch.startswith("refs/heads/"):
                    branch = branch[11:]  # Remove refs/heads/ prefix
                    formatted_line = f"{path} {commit} [branch {branch}]"
                else:
                    formatted_line = f"{path} {commit}"
                worktrees.append(self._parse_worktree_line(formatted_line))

            return worktrees
        except GitCommandError as err:
            raise GitError(
                message="Failed to list worktrees",
                code=ErrorCode.WORKTREE_ERROR,
                cause=err,
            ) from err

    def get_worktree_for_branch(
        self, branch_name: BranchName
    ) -> Optional[WorktreeInfo]:
        """Get worktree information for a branch.

        Parameters
        ----------
        branch_name : str
            Name of the branch

        Returns
        -------
        Optional[WorktreeInfo]
            Worktree information if found, None otherwise

        Raises
        ------
        GitError
            If worktrees cannot be listed
        """
        worktrees = self.list_worktrees()
        return next(
            (wt for wt in worktrees if wt.branch == branch_name),
            None,
        )

    def add_worktree(
        self,
        path: Path,
        branch: Optional[BranchName] = None,
        new_branch: Optional[BranchName] = None,
        commit: Optional[str] = None,
    ) -> None:
        """Add a new worktree.

        Parameters
        ----------
        path : Path
            Path for the new worktree
        branch : Optional[str]
            Existing branch to check out
        new_branch : Optional[str]
            New branch to create
        commit : Optional[str]
            Commit to check out

        Raises
        ------
        GitError
            If worktree cannot be added
        """
        try:
            args = ["add"]
            if new_branch:
                args.extend(["-b", new_branch])
            args.append(str(path))
            if branch:
                args.append(branch)
            elif commit:
                args.append(commit)
            else:
                args.append("HEAD")

            self.repo.git.worktree(*args)
        except GitCommandError as err:
            raise GitError(
                message="Failed to add worktree",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"Path: {path}",
                cause=err,
            ) from err

    def remove_worktree(self, path: Path, force: bool = False) -> None:
        """Remove a worktree.

        Parameters
        ----------
        path : Path
            Path to the worktree
        force : bool
            Force removal even if worktree is dirty

        Raises
        ------
        GitError
            If worktree cannot be removed
        """
        try:
            args = ["remove"]
            if force:
                args.append("--force")
            args.append(str(path))
            self.repo.git.worktree(*args)
        except GitCommandError as err:
            raise GitError(
                message="Failed to remove worktree",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"Path: {path}",
                cause=err,
            ) from err

    def prune_worktrees(self) -> None:
        """Prune all invalid worktrees.

        Raises
        ------
        GitError
            If worktrees cannot be pruned
        """
        try:
            self.repo.git.worktree("prune")
        except GitCommandError as err:
            raise GitError(
                message="Failed to prune worktrees",
                code=ErrorCode.WORKTREE_ERROR,
                cause=err,
            ) from err

    def move_worktree(self, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location.

        Parameters
        ----------
        old_path : Path
            Current path of the worktree
        new_path : Path
            New path for the worktree

        Raises
        ------
        GitError
            If worktree cannot be moved
        """
        try:
            self.repo.git.worktree("move", str(old_path), str(new_path))
        except GitCommandError as err:
            raise GitError(
                message="Failed to move worktree",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"From: {old_path}, To: {new_path}",
                cause=err,
            ) from err

    def lock_worktree(self, path: Path, reason: Optional[str] = None) -> None:
        """Lock a worktree.

        Parameters
        ----------
        path : Path
            Path to the worktree
        reason : Optional[str]
            Reason for locking

        Raises
        ------
        GitError
            If worktree cannot be locked
        """
        try:
            args = ["lock"]
            if reason:
                args.extend(["--reason", reason])
            args.append(str(path))
            self.repo.git.worktree(*args)
        except GitCommandError as err:
            raise GitError(
                message="Failed to lock worktree",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"Path: {path}",
                cause=err,
            ) from err

    def unlock_worktree(self, path: Path) -> None:
        """Unlock a worktree.

        Parameters
        ----------
        path : Path
            Path to the worktree

        Raises
        ------
        GitError
            If worktree cannot be unlocked
        """
        try:
            self.repo.git.worktree("unlock", str(path))
        except GitCommandError as err:
            raise GitError(
                message="Failed to unlock worktree",
                code=ErrorCode.WORKTREE_ERROR,
                details=f"Path: {path}",
                cause=err,
            ) from err
