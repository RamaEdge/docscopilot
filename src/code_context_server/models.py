"""Pydantic models for Code Context MCP Server responses."""

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Information about a git commit."""

    hash: str = Field(description="Commit hash")
    subject: str = Field(description="Commit subject line")
    body: str = Field(default="", description="Commit body")


class FeatureMetadata(BaseModel):
    """Metadata about a feature."""

    feature_id: str = Field(description="Feature identifier")
    commits: list[CommitInfo] = Field(
        default_factory=list, description="Commits related to feature"
    )
    branches: list[str] = Field(
        default_factory=list, description="Branches containing feature commits"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags containing feature commits"
    )
    code_paths: list[str] = Field(
        default_factory=list, description="Code files changed for feature"
    )
    test_paths: list[str] = Field(
        default_factory=list, description="Test files related to feature"
    )
    description: str | None = Field(
        default=None, description="Feature description from commit messages"
    )
    related_issues: list[str] = Field(
        default_factory=list, description="Related issue/PR references"
    )


class CodeExample(BaseModel):
    """A code example extracted from source code."""

    type: str = Field(description="Type of code element (function, class, etc.)")
    name: str = Field(description="Name of the code element")
    code: str = Field(description="Source code")
    docstring: str | None = Field(default=None, description="Docstring if available")
    line_numbers: tuple[int, int] = Field(description="Start and end line numbers")


class CodeExamples(BaseModel):
    """Code examples from a file."""

    path: str = Field(description="File path")
    examples: list[CodeExample] = Field(
        default_factory=list, description="List of code examples"
    )


class EndpointInfo(BaseModel):
    """Information about an API endpoint."""

    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="API path")
    function: str = Field(description="Function name handling the endpoint")
    file: str = Field(description="File containing the endpoint")
    signature: str | None = Field(default=None, description="Function signature")
    status: str = Field(description="Status: new, modified, or deleted")
    line_numbers: tuple[int, int] = Field(description="Start and end line numbers")


class ChangedEndpoints(BaseModel):
    """Changed API endpoints from a diff."""

    endpoints: list[EndpointInfo] = Field(
        default_factory=list, description="List of changed endpoints"
    )
