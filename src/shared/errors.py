"""Custom exceptions for DocsCopilot MCP servers."""


class DocsCopilotError(Exception):
    """Base exception for DocsCopilot errors."""

    def __init__(self, message: str, details: str | None = None):
        """Initialize error with message and optional details."""
        self.message = message
        self.details = details
        super().__init__(self.message)


class RepositoryNotFoundError(DocsCopilotError):
    """Raised when a repository is not found in workspace."""

    pass


class FileNotFoundError(DocsCopilotError):
    """Raised when a file is not found."""

    pass


class GitCommandError(DocsCopilotError):
    """Raised when a git command fails."""

    pass


class FeatureNotFoundError(DocsCopilotError):
    """Raised when a feature ID is not found."""

    pass


class ConfigurationError(DocsCopilotError):
    """Raised when configuration is invalid."""

    pass


class TemplateNotFoundError(DocsCopilotError):
    """Raised when a template is not found."""

    pass


class InvalidPathError(DocsCopilotError):
    """Raised when a path is invalid or unsafe."""

    pass
