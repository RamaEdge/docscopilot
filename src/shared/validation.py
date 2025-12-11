"""Input validation utilities."""

import re
from pathlib import Path

from src.shared.errors import InvalidPathError, ValidationError


def validate_path(path: str | Path, workspace_root: Path) -> Path:
    """Validate and normalize a file path.

    Args:
        path: Path to validate (can be string or Path)
        workspace_root: Root workspace directory

    Returns:
        Normalized Path object

    Raises:
        InvalidPathError: If path is invalid or unsafe
    """
    if isinstance(path, str):
        path = Path(path)

    # Resolve path
    if not path.is_absolute():
        resolved_path = workspace_root / path
    else:
        resolved_path = path.resolve()

    # Ensure path is within workspace for security
    try:
        resolved_path.relative_to(workspace_root.resolve())
    except ValueError as e:
        raise InvalidPathError(
            f"Path outside workspace: {path}",
            f"File must be within workspace: {workspace_root}",
        ) from e

    # Validate path doesn't contain dangerous patterns
    path_str = str(resolved_path.relative_to(workspace_root))
    if ".." in path_str or path_str.startswith("/"):
        raise InvalidPathError(
            f"Invalid path: {path}",
            "Path contains '..' or starts with '/' which is not allowed",
        )

    return resolved_path


def validate_feature_id(feature_id: str) -> str:
    """Validate feature ID format.

    Args:
        feature_id: Feature identifier to validate

    Returns:
        Validated feature ID

    Raises:
        ValidationError: If feature ID is invalid
    """
    if not feature_id:
        raise ValidationError(
            "Feature ID cannot be empty",
            "feature_id must be a non-empty string",
        )

    if not isinstance(feature_id, str):
        raise ValidationError(
            f"Feature ID must be a string, got {type(feature_id).__name__}",
            f"Invalid type: {type(feature_id)}",
        )

    # Feature IDs should be alphanumeric with dashes, underscores, and slashes
    if not re.match(r"^[a-zA-Z0-9_\-/]+$", feature_id):
        raise ValidationError(
            f"Invalid feature ID format: {feature_id}",
            "Feature ID can only contain alphanumeric characters, dashes, underscores, and slashes",
        )

    if len(feature_id) > 200:
        raise ValidationError(
            f"Feature ID too long: {len(feature_id)} characters",
            "Feature ID must be 200 characters or less",
        )

    return feature_id.strip()


def validate_doc_type(doc_type: str | None) -> str:
    """Validate document type.

    Args:
        doc_type: Document type to validate

    Returns:
        Validated document type

    Raises:
        ValidationError: If document type is invalid
    """
    valid_types = [
        "concept",
        "task",
        "api_reference",
        "release_notes",
        "feature_overview",
        "configuration_reference",
    ]

    if doc_type is None:
        return "concept"  # Default

    if not isinstance(doc_type, str):
        raise ValidationError(
            f"Document type must be a string, got {type(doc_type).__name__}",
            f"Invalid type: {type(doc_type)}",
        )

    doc_type = doc_type.lower().strip()
    if doc_type not in valid_types:
        raise ValidationError(
            f"Invalid document type: {doc_type}",
            f"Valid types are: {', '.join(valid_types)}",
        )

    return doc_type


def validate_branch_name(branch_name: str) -> str:
    """Validate git branch name.

    Args:
        branch_name: Branch name to validate

    Returns:
        Validated branch name

    Raises:
        ValidationError: If branch name is invalid
    """
    if not branch_name:
        raise ValidationError(
            "Branch name cannot be empty",
            "branch_name must be a non-empty string",
        )

    if not isinstance(branch_name, str):
        raise ValidationError(
            f"Branch name must be a string, got {type(branch_name).__name__}",
            f"Invalid type: {type(branch_name)}",
        )

    # Git branch name rules
    if branch_name.startswith(".") or branch_name.endswith("."):
        raise ValidationError(
            f"Invalid branch name: {branch_name}",
            "Branch name cannot start or end with a dot",
        )

    if ".." in branch_name or "~" in branch_name or "^" in branch_name:
        raise ValidationError(
            f"Invalid branch name: {branch_name}",
            "Branch name cannot contain '..', '~', or '^'",
        )

    if len(branch_name) > 255:
        raise ValidationError(
            f"Branch name too long: {len(branch_name)} characters",
            "Branch name must be 255 characters or less",
        )

    return branch_name.strip()
