"""Pydantic models for Docs Repo MCP Server responses."""

from pydantic import BaseModel, Field


class DocLocation(BaseModel):
    """Suggested documentation location."""

    path: str = Field(description="Suggested file path")
    doc_type: str = Field(description="Document type")
    reason: str = Field(description="Reason for suggestion")


class WriteResult(BaseModel):
    """Result of writing a document."""

    path: str = Field(description="Path where document was written")
    success: bool = Field(description="Whether write was successful")
    message: str = Field(description="Status message")


class PRResult(BaseModel):
    """Result of creating a pull request."""

    pr_url: str = Field(description="URL of the created pull request")
    branch: str = Field(description="Branch name")
    pr_number: int | None = Field(default=None, description="PR number")
    success: bool = Field(description="Whether PR creation was successful")
    message: str = Field(description="Status message")
