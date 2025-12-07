"""Configuration management for MCP servers."""

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ServerConfig(BaseModel):
    """Base configuration for MCP servers."""

    workspace_root: Path = Field(
        default_factory=lambda: Path(os.getcwd()),
        description="Root directory containing repositories",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    @field_validator("workspace_root", mode="before")
    @classmethod
    def validate_workspace_root(cls, v: str | Path) -> Path:
        """Convert workspace_root to Path."""
        if isinstance(v, str):
            return Path(v)
        return v

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables."""
        return cls(
            workspace_root=Path(os.getenv("WORKSPACE_ROOT", os.getcwd())),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
        )


class CodeContextConfig(ServerConfig):
    """Configuration for Code Context MCP Server."""

    git_binary: str = Field(default="git", description="Path to git binary")
    supported_languages: list[str] = Field(
        default_factory=lambda: ["python"],
        description="Supported programming languages",
    )

    @classmethod
    def from_env(cls) -> "CodeContextConfig":
        """Create configuration from environment variables."""
        base_config = super().from_env()
        languages_str = os.getenv("SUPPORTED_LANGUAGES", "python")
        languages = [lang.strip() for lang in languages_str.split(",") if lang.strip()]

        return cls(
            **base_config.model_dump(),
            git_binary=os.getenv("GIT_BINARY", "git"),
            supported_languages=languages,
        )


class TemplatesStyleConfig(ServerConfig):
    """Configuration for Templates + Style MCP Server."""

    templates_path: Path | None = Field(
        default=None,
        description="Optional path to external templates repository",
    )

    @field_validator("templates_path", mode="before")
    @classmethod
    def validate_templates_path(cls, v: str | Path | None) -> Path | None:
        """Convert templates_path to Path."""
        if v is None:
            return None
        if isinstance(v, str):
            return Path(v)
        return v

    @classmethod
    def from_env(cls) -> "TemplatesStyleConfig":
        """Create configuration from environment variables."""
        base_config = super().from_env()
        templates_path = os.getenv("DOCSCOPILOT_TEMPLATES_PATH")

        return cls(
            **base_config.model_dump(),
            templates_path=Path(templates_path) if templates_path else None,
        )


class DocsRepoConfig(ServerConfig):
    """Configuration for Docs Repo MCP Server."""

    github_token: str | None = Field(
        default=None, description="GitHub personal access token"
    )
    gitlab_token: str | None = Field(
        default=None, description="GitLab personal access token"
    )

    @classmethod
    def from_env(cls) -> "DocsRepoConfig":
        """Create configuration from environment variables."""
        base_config = super().from_env()

        return cls(
            **base_config.model_dump(),
            github_token=os.getenv("GITHUB_TOKEN"),
            gitlab_token=os.getenv("GITLAB_TOKEN"),
        )
