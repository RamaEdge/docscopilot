"""Security utilities for input validation and sanitization."""

import re
from pathlib import Path


class SecurityError(Exception):
    """Raised when security validation fails."""

    def __init__(self, message: str, details: str | None = None):
        """Initialize security error with message and optional details."""
        self.message = message
        self.details = details
        super().__init__(self.message)


class SecurityValidator:
    """Validates and sanitizes user inputs to prevent security vulnerabilities."""

    # Feature ID pattern: alphanumeric, hyphens, underscores, forward slashes
    # Max length to prevent DoS
    FEATURE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-/]{1,200}$")
    FEATURE_ID_MAX_LENGTH = 200

    # Branch name pattern: alphanumeric, hyphens, underscores, forward slashes
    # Git branch names can't contain spaces or special chars except -_/
    BRANCH_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-/]{1,255}$")
    BRANCH_NAME_MAX_LENGTH = 255

    # Product name pattern: alphanumeric, hyphens, underscores
    PRODUCT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,100}$")
    PRODUCT_NAME_MAX_LENGTH = 100

    # Doc type must be from allowed list
    ALLOWED_DOC_TYPES = {
        "concept",
        "task",
        "api_reference",
        "release_notes",
        "feature_overview",
        "configuration_reference",
    }

    @classmethod
    def validate_feature_id(cls, feature_id: str) -> str:
        """Validate and sanitize feature ID.

        Args:
            feature_id: Feature identifier to validate

        Returns:
            Sanitized feature ID

        Raises:
            SecurityError: If feature ID is invalid or unsafe
        """
        if not isinstance(feature_id, str):
            raise SecurityError(
                "Invalid feature_id type",
                "feature_id must be a string",
            )

        feature_id = feature_id.strip()

        if not feature_id:
            raise SecurityError(
                "Empty feature_id",
                "feature_id cannot be empty",
            )

        if len(feature_id) > cls.FEATURE_ID_MAX_LENGTH:
            raise SecurityError(
                f"Feature ID too long (max {cls.FEATURE_ID_MAX_LENGTH} characters)",
                f"Received {len(feature_id)} characters",
            )

        if not cls.FEATURE_ID_PATTERN.match(feature_id):
            raise SecurityError(
                "Invalid feature_id format",
                "feature_id can only contain alphanumeric characters, hyphens, underscores, and forward slashes",
            )

        # Additional checks for dangerous patterns
        dangerous_patterns = ["..", "\x00", "\n", "\r", "\t"]
        for pattern in dangerous_patterns:
            if pattern in feature_id:
                raise SecurityError(
                    "Invalid feature_id contains dangerous characters",
                    f"feature_id cannot contain: {pattern!r}",
                )

        return feature_id

    @classmethod
    def validate_branch_name(cls, branch_name: str) -> str:
        """Validate and sanitize git branch name.

        Args:
            branch_name: Branch name to validate

        Returns:
            Sanitized branch name

        Raises:
            SecurityError: If branch name is invalid or unsafe
        """
        if not isinstance(branch_name, str):
            raise SecurityError(
                "Invalid branch_name type",
                "branch_name must be a string",
            )

        branch_name = branch_name.strip()

        if not branch_name:
            raise SecurityError(
                "Empty branch_name",
                "branch_name cannot be empty",
            )

        if len(branch_name) > cls.BRANCH_NAME_MAX_LENGTH:
            raise SecurityError(
                f"Branch name too long (max {cls.BRANCH_NAME_MAX_LENGTH} characters)",
                f"Received {len(branch_name)} characters",
            )

        # Git branch name restrictions
        if branch_name.startswith(".") or branch_name.endswith("."):
            raise SecurityError(
                "Invalid branch name",
                "Branch name cannot start or end with a dot",
            )

        if branch_name.endswith(".lock"):
            raise SecurityError(
                "Invalid branch name",
                "Branch name cannot end with .lock",
            )

        if ".." in branch_name or "@{" in branch_name:
            raise SecurityError(
                "Invalid branch name",
                "Branch name cannot contain '..' or '@{'",
            )

        if not cls.BRANCH_NAME_PATTERN.match(branch_name):
            raise SecurityError(
                "Invalid branch_name format",
                "branch_name can only contain alphanumeric characters, hyphens, underscores, and forward slashes",
            )

        return branch_name

    @classmethod
    def validate_product_name(cls, product_name: str | None) -> str | None:
        """Validate and sanitize product name.

        Args:
            product_name: Product name to validate (can be None)

        Returns:
            Sanitized product name or None

        Raises:
            SecurityError: If product name is invalid or unsafe
        """
        if product_name is None:
            return None

        if not isinstance(product_name, str):
            raise SecurityError(
                "Invalid product_name type",
                "product_name must be a string or None",
            )

        product_name = product_name.strip()

        if not product_name:
            return None

        if len(product_name) > cls.PRODUCT_NAME_MAX_LENGTH:
            raise SecurityError(
                f"Product name too long (max {cls.PRODUCT_NAME_MAX_LENGTH} characters)",
                f"Received {len(product_name)} characters",
            )

        if not cls.PRODUCT_NAME_PATTERN.match(product_name):
            raise SecurityError(
                "Invalid product_name format",
                "product_name can only contain alphanumeric characters, hyphens, and underscores",
            )

        return product_name

    @classmethod
    def validate_doc_type(cls, doc_type: str) -> str:
        """Validate document type.

        Args:
            doc_type: Document type to validate

        Returns:
            Validated doc_type

        Raises:
            SecurityError: If doc_type is invalid
        """
        if not isinstance(doc_type, str):
            raise SecurityError(
                "Invalid doc_type type",
                "doc_type must be a string",
            )

        doc_type = doc_type.strip().lower()

        if doc_type not in cls.ALLOWED_DOC_TYPES:
            raise SecurityError(
                f"Invalid doc_type: {doc_type}",
                f"Allowed types are: {', '.join(sorted(cls.ALLOWED_DOC_TYPES))}",
            )

        return doc_type

    @classmethod
    def validate_path(cls, path: str, workspace_root: Path) -> Path:
        """Validate and sanitize file path to prevent path traversal attacks.

        Args:
            path: File path to validate
            workspace_root: Root directory that path must be within

        Returns:
            Resolved and validated Path object

        Raises:
            SecurityError: If path is invalid or unsafe
        """
        if not isinstance(path, str):
            raise SecurityError(
                "Invalid path type",
                "path must be a string",
            )

        path = path.strip()

        if not path:
            raise SecurityError(
                "Empty path",
                "path cannot be empty",
            )

        # Check for dangerous patterns
        dangerous_patterns = ["\x00", "\n", "\r"]
        for pattern in dangerous_patterns:
            if pattern in path:
                raise SecurityError(
                    "Invalid path contains dangerous characters",
                    f"path cannot contain: {pattern!r}",
                )

        # Resolve path
        file_path = Path(path)

        # If relative, resolve against workspace_root
        if not file_path.is_absolute():
            file_path = workspace_root / file_path
        else:
            # For absolute paths, ensure they're within workspace
            try:
                file_path.resolve().relative_to(workspace_root.resolve())
            except ValueError as err:
                raise SecurityError(
                    f"Path outside workspace: {path}",
                    f"File must be within workspace: {workspace_root}",
                ) from err

        # Resolve to absolute path and normalize
        resolved_path = file_path.resolve()

        # Ensure resolved path is still within workspace
        try:
            resolved_path.relative_to(workspace_root.resolve())
        except ValueError as err:
            raise SecurityError(
                f"Path outside workspace: {path}",
                f"Resolved path {resolved_path} is outside workspace: {workspace_root}",
            ) from err

        # Check for path traversal attempts in relative path
        relative_path = resolved_path.relative_to(workspace_root.resolve())
        if ".." in str(relative_path):
            raise SecurityError(
                f"Invalid path contains '..': {path}",
                "Path traversal is not allowed",
            )

        return resolved_path

    @classmethod
    def sanitize_git_pattern(cls, pattern: str) -> str:
        """Sanitize pattern used in git commands to prevent injection.

        Args:
            pattern: Pattern to sanitize

        Returns:
            Sanitized pattern

        Raises:
            SecurityError: If pattern is invalid or unsafe
        """
        if not isinstance(pattern, str):
            raise SecurityError(
                "Invalid pattern type",
                "pattern must be a string",
            )

        pattern = pattern.strip()

        if not pattern:
            raise SecurityError(
                "Empty pattern",
                "pattern cannot be empty",
            )

        # Check for command injection attempts
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]
        for char in dangerous_chars:
            if char in pattern:
                raise SecurityError(
                    "Invalid pattern contains dangerous characters",
                    f"pattern cannot contain: {char!r}",
                )

        return pattern

    @classmethod
    def sanitize_commit_hash(cls, commit_hash: str) -> str:
        """Sanitize git commit hash to prevent injection.

        Args:
            commit_hash: Commit hash to sanitize

        Returns:
            Sanitized commit hash

        Raises:
            SecurityError: If commit hash is invalid
        """
        if not isinstance(commit_hash, str):
            raise SecurityError(
                "Invalid commit_hash type",
                "commit_hash must be a string",
            )

        commit_hash = commit_hash.strip()

        if not commit_hash:
            raise SecurityError(
                "Empty commit_hash",
                "commit_hash cannot be empty",
            )

        # Git commit hashes are hex strings, typically 7-40 characters
        # Allow alphanumeric only
        if not re.match(r"^[a-fA-F0-9]{7,40}$", commit_hash):
            raise SecurityError(
                "Invalid commit hash format",
                "commit_hash must be a valid git commit hash (7-40 hex characters)",
            )

        return commit_hash
