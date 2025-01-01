"""Error handling for arborist."""

from enum import Enum, auto
from typing import Optional


class ErrorCode(Enum):
    """Error codes for arborist."""

    # Git errors
    INVALID_REPOSITORY = auto()
    BRANCH_NOT_FOUND = auto()
    BRANCH_EXISTS = auto()
    BRANCH_PROTECTED = auto()
    BRANCH_CURRENT = auto()
    BRANCH_NOT_MERGED = auto()
    BRANCH_INVALID_NAME = auto()
    WORKTREE_ERROR = auto()
    REMOTE_ERROR = auto()
    FETCH_ERROR = auto()
    MERGE_ERROR = auto()

    # Configuration errors
    CONFIG_INVALID = auto()
    CONFIG_NOT_FOUND = auto()
    CONFIG_PERMISSION = auto()

    # Runtime errors
    TYPE_ERROR = auto()
    VALUE_ERROR = auto()
    RUNTIME_ERROR = auto()


class ArboristError(Exception):
    """Base exception for all arborist errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        details: Optional[str] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize error.

        Parameters
        ----------
        message : str
            Error message
        code : ErrorCode
            Error code
        details : Optional[str]
            Additional error details
        cause : Optional[Exception]
            Original exception that caused this error
        """
        self.message = message
        self.code = code
        self.details = details
        self.cause = cause
        super().__init__(self.full_message)

    @property
    def full_message(self) -> str:
        """Get full error message including details.

        Returns
        -------
        str
            Full error message
        """
        msg = f"{self.code.name}: {self.message}"
        if self.details:
            msg = f"{msg}\nDetails: {self.details}"
        if self.cause:
            msg = f"{msg}\nCause: {str(self.cause)}"
        return msg


class GitError(ArboristError):
    """Git operation error."""

    pass


class ConfigError(ArboristError):
    """Configuration error."""

    pass


class ValidationError(ArboristError):
    """Validation error."""

    pass


class RuntimeError(ArboristError):
    """Runtime error."""

    pass
