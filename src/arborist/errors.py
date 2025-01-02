"""Custom error types for the arborist package."""

from enum import Enum, auto
from typing import Optional


class ErrorCode(Enum):
    """Error codes for git operations."""

    # Git errors
    BRANCH_ERROR = auto()
    REPO_ERROR = auto()
    MERGE_ERROR = auto()
    CHECKOUT_ERROR = auto()
    FETCH_ERROR = auto()
    PULL_ERROR = auto()
    PUSH_ERROR = auto()
    REBASE_ERROR = auto()
    RESET_ERROR = auto()
    STASH_ERROR = auto()
    TAG_ERROR = auto()

    # Configuration errors
    CONFIG_INVALID = auto()
    CONFIG_NOT_FOUND = auto()
    CONFIG_PERMISSION = auto()

    UNKNOWN_ERROR = auto()


class GitError(Exception):
    """Custom error type for git operations."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize git error.

        Parameters
        ----------
        message : str
            Error message
        code : ErrorCode, optional
            Error code, by default ErrorCode.UNKNOWN_ERROR
        details : Optional[str], optional
            Additional error details, by default None
        cause : Optional[Exception], optional
            Original exception that caused this error, by default None
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details
        self.cause = cause


class ConfigError(GitError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.CONFIG_INVALID,
        details: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize configuration error.

        Parameters
        ----------
        message : str
            Error message
        code : ErrorCode, optional
            Error code, by default ErrorCode.CONFIG_INVALID
        details : Optional[str], optional
            Additional error details, by default None
        cause : Optional[Exception], optional
            Original exception that caused this error, by default None
        """
        super().__init__(message, code, details, cause)
