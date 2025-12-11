"""Custom exceptions for DocsCopilot MCP servers."""

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for DocsCopilot errors."""

    # Repository errors (1xxx)
    REPOSITORY_NOT_FOUND = "REPO_1001"
    GIT_COMMAND_FAILED = "REPO_1002"
    GIT_TIMEOUT = "REPO_1003"

    # File errors (2xxx)
    FILE_NOT_FOUND = "FILE_2001"
    INVALID_PATH = "FILE_2002"
    PERMISSION_DENIED = "FILE_2003"

    # Feature errors (3xxx)
    FEATURE_NOT_FOUND = "FEATURE_3001"

    # Template errors (4xxx)
    TEMPLATE_NOT_FOUND = "TEMPLATE_4001"
    TEMPLATE_LOAD_ERROR = "TEMPLATE_4002"

    # Configuration errors (5xxx)
    CONFIGURATION_INVALID = "CONFIG_5001"
    CONFIGURATION_MISSING = "CONFIG_5002"

    # API errors (6xxx)
    API_REQUEST_FAILED = "API_6001"
    API_TIMEOUT = "API_6002"
    API_RATE_LIMIT = "API_6003"
    API_AUTHENTICATION_FAILED = "API_6004"

    # Validation errors (7xxx)
    VALIDATION_ERROR = "VALID_7001"
    INVALID_INPUT = "VALID_7002"

    # Unknown errors (9xxx)
    UNKNOWN_ERROR = "UNKNOWN_9001"


class DocsCopilotError(Exception):
    """Base exception for DocsCopilot errors."""

    def __init__(
        self,
        message: str,
        details: str | None = None,
        error_code: ErrorCode | None = None,
    ):
        """Initialize error with message, optional details, and error code.

        Args:
            message: User-friendly error message
            details: Technical details for debugging
            error_code: Error code for programmatic handling
        """
        self.message = message
        self.details = details
        self.error_code = error_code or ErrorCode.UNKNOWN_ERROR
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        """Convert error to dictionary for JSON serialization."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code.value,
        }
        if self.details:
            result["details"] = self.details
        return result


class RepositoryNotFoundError(DocsCopilotError):
    """Raised when a repository is not found in workspace."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.REPOSITORY_NOT_FOUND)


class FileNotFoundError(DocsCopilotError):
    """Raised when a file is not found."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.FILE_NOT_FOUND)


class GitCommandError(DocsCopilotError):
    """Raised when a git command fails."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.GIT_COMMAND_FAILED)


class GitTimeoutError(DocsCopilotError):
    """Raised when a git command times out."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.GIT_TIMEOUT)


class FeatureNotFoundError(DocsCopilotError):
    """Raised when a feature ID is not found."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.FEATURE_NOT_FOUND)


class ConfigurationError(DocsCopilotError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.CONFIGURATION_INVALID)


class TemplateNotFoundError(DocsCopilotError):
    """Raised when a template is not found."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.TEMPLATE_NOT_FOUND)


class InvalidPathError(DocsCopilotError):
    """Raised when a path is invalid or unsafe."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.INVALID_PATH)


class ValidationError(DocsCopilotError):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: str | None = None):
        super().__init__(message, details, error_code=ErrorCode.VALIDATION_ERROR)


class APIError(DocsCopilotError):
    """Raised when an API call fails."""

    def __init__(
        self,
        message: str,
        details: str | None = None,
        error_code: ErrorCode | None = None,
    ):
        super().__init__(
            message,
            details,
            error_code=error_code or ErrorCode.API_REQUEST_FAILED,
        )
