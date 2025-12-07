"""Pydantic models for Templates + Style MCP Server responses."""

from typing import Any

from pydantic import BaseModel, Field


class Template(BaseModel):
    """A documentation template."""

    doc_type: str = Field(
        description="Document type (concept, task, api_reference, etc.)"
    )
    content: str = Field(description="Template content (Jinja2)")
    source: str = Field(
        description="Source of template (configured, workspace, default)"
    )


class StyleGuide(BaseModel):
    """Style guide configuration."""

    product: str | None = Field(default=None, description="Product name")
    heading_structure: dict[str, Any] = Field(
        default_factory=dict, description="Heading structure rules"
    )
    tone: dict[str, Any] = Field(default_factory=dict, description="Tone guidelines")
    formatting: dict[str, Any] = Field(
        default_factory=dict, description="Formatting rules"
    )
    source: str = Field(
        description="Source of style guide (configured, workspace, default)"
    )


class Glossary(BaseModel):
    """Glossary of terms."""

    terms: dict[str, str] = Field(default_factory=dict, description="Term definitions")
    source: str = Field(
        description="Source of glossary (configured, workspace, default)"
    )
