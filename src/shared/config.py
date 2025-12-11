"""Configuration management for MCP servers."""

import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, field_validator

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


class ServerConfig(BaseModel):
    """Base configuration for MCP servers."""

    workspace_root: Path = Field(
        default_factory=lambda: Path(os.getcwd()),
        description="Root directory containing repositories",
    )
    log_level: str = Field(default="INFO", description="Logging level")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    git_command_timeout: int = Field(
        default=30, description="Timeout for git commands in seconds"
    )
    api_request_timeout: int = Field(
        default=30, description="Timeout for API requests in seconds"
    )

    @field_validator("workspace_root", mode="before")
    @classmethod
    def validate_workspace_root(cls, v: str | Path) -> Path:
        """Convert workspace_root to Path."""
        if isinstance(v, str):
            return Path(v)
        return v

    @field_validator("git_command_timeout", "api_request_timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if not isinstance(v, int):
            raise ValueError("Timeout must be an integer")
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        if v > 3600:  # 1 hour max
            raise ValueError("Timeout cannot exceed 3600 seconds (1 hour)")
        return v

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables."""
        return cls(
            workspace_root=Path(os.getenv("WORKSPACE_ROOT", os.getcwd())),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            git_command_timeout=int(os.getenv("GIT_COMMAND_TIMEOUT", "30")),
            api_request_timeout=int(os.getenv("API_REQUEST_TIMEOUT", "30")),
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "ServerConfig":
        """Load configuration from YAML or TOML file.

        Args:
            config_path: Path to configuration file

        Returns:
            ServerConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is unsupported
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        suffix = config_path.suffix.lower()
        if suffix == ".yaml" or suffix == ".yml":
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            if tomllib is None:
                raise ValueError("TOML support requires Python 3.11+ or tomli package")
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(
                f"Unsupported configuration file format: {suffix}. "
                "Supported formats: .yaml, .yml, .toml"
            )

        # Extract server config section and merge with defaults
        server_config = data.get("server", {})
        # Start with defaults, then update with file values
        default_config = cls()
        config_dict = default_config.model_dump()
        # Update with file values (only keys present in file)
        for key, value in server_config.items():
            if hasattr(default_config, key):
                config_dict[key] = value
        return cls(**config_dict)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "ServerConfig":
        """Load configuration with priority: env vars > config file > defaults.

        Args:
            config_path: Optional path to configuration file

        Returns:
            ServerConfig instance
        """
        # Start with defaults
        config_dict = cls().model_dump()

        # Load from file if provided (file values override defaults)
        if config_path and config_path.exists():
            file_config = cls.from_file(config_path)
            file_dict = file_config.model_dump()
            # Merge file config
            for key, value in file_dict.items():
                config_dict[key] = value

        # Load from environment (only override if env vars are actually set)
        # Check each env var individually to avoid overriding with defaults
        if "WORKSPACE_ROOT" in os.environ:
            workspace_root = os.getenv("WORKSPACE_ROOT")
            if workspace_root:
                config_dict["workspace_root"] = Path(workspace_root)
        if "LOG_LEVEL" in os.environ:
            log_level = os.getenv("LOG_LEVEL")
            if log_level:
                config_dict["log_level"] = log_level
        if "HOST" in os.environ:
            host = os.getenv("HOST")
            if host:
                config_dict["host"] = host
        if "PORT" in os.environ:
            port_str = os.getenv("PORT")
            if port_str:
                config_dict["port"] = int(port_str)
        if "GIT_COMMAND_TIMEOUT" in os.environ:
            timeout_str = os.getenv("GIT_COMMAND_TIMEOUT")
            if timeout_str:
                config_dict["git_command_timeout"] = int(timeout_str)
        if "API_REQUEST_TIMEOUT" in os.environ:
            timeout_str = os.getenv("API_REQUEST_TIMEOUT")
            if timeout_str:
                config_dict["api_request_timeout"] = int(timeout_str)

        return cls(**config_dict)


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

        config_dict = base_config.model_dump()
        config_dict["git_binary"] = os.getenv("GIT_BINARY", "git")
        config_dict["supported_languages"] = languages
        return cls(**config_dict)

    @classmethod
    def from_file(cls, config_path: Path) -> "CodeContextConfig":
        """Load configuration from YAML or TOML file."""
        base_config = super().from_file(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        suffix = config_path.suffix.lower()
        if suffix == ".yaml" or suffix == ".yml":
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            if tomllib is None:
                raise ValueError("TOML support requires Python 3.11+ or tomli package")
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")

        code_context_config = data.get("code_context", {})
        config_dict = base_config.model_dump()
        config_dict.update(code_context_config)

        # Handle supported_languages list
        if "supported_languages" in config_dict:
            if isinstance(config_dict["supported_languages"], str):
                config_dict["supported_languages"] = [
                    lang.strip()
                    for lang in config_dict["supported_languages"].split(",")
                    if lang.strip()
                ]

        return cls(**config_dict)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "CodeContextConfig":
        """Load configuration with priority: env vars > config file > defaults."""
        config = cls()
        if config_path:
            file_config = cls.from_file(config_path)
            config = cls(**{**config.model_dump(), **file_config.model_dump()})
        env_config = cls.from_env()
        return cls(**{**config.model_dump(), **env_config.model_dump()})


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

        config_dict = base_config.model_dump()
        config_dict["templates_path"] = Path(templates_path) if templates_path else None
        return cls(**config_dict)

    @classmethod
    def from_file(cls, config_path: Path) -> "TemplatesStyleConfig":
        """Load configuration from YAML or TOML file."""
        base_config = super().from_file(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        suffix = config_path.suffix.lower()
        if suffix == ".yaml" or suffix == ".yml":
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            if tomllib is None:
                raise ValueError("TOML support requires Python 3.11+ or tomli package")
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")

        templates_style_config = data.get("templates_style", {})
        config_dict = base_config.model_dump()
        config_dict.update(templates_style_config)

        # Handle templates_path
        if "templates_path" in config_dict and config_dict["templates_path"]:
            config_dict["templates_path"] = Path(config_dict["templates_path"])

        return cls(**config_dict)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "TemplatesStyleConfig":
        """Load configuration with priority: env vars > config file > defaults."""
        config = cls()
        if config_path:
            file_config = cls.from_file(config_path)
            config = cls(**{**config.model_dump(), **file_config.model_dump()})
        env_config = cls.from_env()
        return cls(**{**config.model_dump(), **env_config.model_dump()})


class RetryConfig(BaseModel):
    """Configuration for API retry strategy."""

    total: int = Field(default=3, description="Total number of retry attempts")
    backoff_factor: int = Field(
        default=1, description="Backoff factor for exponential backoff"
    )
    status_forcelist: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger a retry",
    )

    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int) -> int:
        """Validate retry total."""
        if not isinstance(v, int):
            raise ValueError("Total must be an integer")
        if v < 0:
            raise ValueError("Total cannot be negative")
        if v > 10:
            raise ValueError("Total cannot exceed 10 retries")
        return v

    @field_validator("backoff_factor")
    @classmethod
    def validate_backoff_factor(cls, v: int) -> int:
        """Validate backoff factor."""
        if not isinstance(v, int):
            raise ValueError("Backoff factor must be an integer")
        if v < 0:
            raise ValueError("Backoff factor cannot be negative")
        if v > 10:
            raise ValueError("Backoff factor cannot exceed 10")
        return v

    @field_validator("status_forcelist")
    @classmethod
    def validate_status_codes(cls, v: list[int]) -> list[int]:
        """Validate HTTP status codes."""
        if not isinstance(v, list):
            raise ValueError("Status forcelist must be a list")
        valid_status_codes = set(range(100, 600))  # Valid HTTP status code range
        # Pydantic ensures v is list[int] before this validator runs
        for code in v:
            if code not in valid_status_codes:
                raise ValueError(f"Invalid HTTP status code: {code}")
        return sorted(set(v))  # Remove duplicates and sort


class DocsRepoConfig(ServerConfig):
    """Configuration for Docs Repo MCP Server."""

    github_token: str | None = Field(
        default=None,
        description="GitHub personal access token",
        exclude=True,  # Exclude from serialization to prevent accidental exposure
    )
    gitlab_token: str | None = Field(
        default=None,
        description="GitLab personal access token",
        exclude=True,  # Exclude from serialization to prevent accidental exposure
    )
    github_api_base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL (supports GitHub Enterprise)",
    )
    gitlab_api_base_url: str = Field(
        default="https://gitlab.com/api/v4",
        description="GitLab API base URL (supports self-hosted GitLab)",
    )
    github_host: str = Field(
        default="github.com",
        description="GitHub hostname (for parsing remote URLs)",
    )
    gitlab_host: str = Field(
        default="gitlab.com",
        description="GitLab hostname (for parsing remote URLs)",
    )

    @field_validator("github_api_base_url", "gitlab_api_base_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        """Validate API base URL format."""
        if not isinstance(v, str):
            raise ValueError("URL must be a string")
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        # Parse URL
        parsed = urlparse(v)
        # Must be HTTPS (security requirement)
        if parsed.scheme != "https":
            raise ValueError("API URL must use HTTPS scheme")
        # Must have netloc
        if not parsed.netloc:
            raise ValueError("Invalid URL format: missing hostname")
        # Check for dangerous patterns
        if any(char in v for char in ["\x00", "\n", "\r", "\t"]):
            raise ValueError("URL contains dangerous characters")
        # Length limit
        if len(v) > 500:
            raise ValueError("URL too long (max 500 characters)")
        return v

    @field_validator("github_host", "gitlab_host")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        """Validate hostname format (RFC 1123)."""
        if not isinstance(v, str):
            raise ValueError("Hostname must be a string")
        v = v.strip().lower()
        if not v:
            raise ValueError("Hostname cannot be empty")
        # Basic hostname validation (RFC 1123)
        hostname_pattern = r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*$"
        if not re.match(hostname_pattern, v):
            raise ValueError("Invalid hostname format")
        # Length limit (RFC 1123: max 253 characters)
        if len(v) > 253:
            raise ValueError("Hostname too long (max 253 characters)")
        # Check for dangerous patterns
        if any(char in v for char in ["\x00", "\n", "\r", "\t", " "]):
            raise ValueError("Hostname contains dangerous characters")
        return v

    default_doc_type: str = Field(
        default="concept",
        description="Default document type when not specified",
    )
    doc_type_directories: dict[str, str] = Field(
        default_factory=lambda: {
            "concept": "concepts",
            "task": "tasks",
            "api_reference": "api",
            "release_notes": "releases",
            "feature_overview": "features",
            "configuration_reference": "configuration",
        },
        description="Mapping of document types to directory names",
    )
    default_base_branch: str = Field(
        default="main",
        description="Default base branch for pull requests",
    )
    docs_directory: str = Field(
        default="docs", description="Directory name for documentation files"
    )
    api_retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="API retry configuration",
    )
    repo_mode: Literal["same", "external"] = Field(
        default="same",
        description="Repository mode: 'same' or 'external'",
    )

    @field_validator("docs_directory")
    @classmethod
    def validate_docs_directory(cls, v: str) -> str:
        """Validate docs directory name."""
        if not isinstance(v, str):
            raise ValueError("Directory name must be a string")
        v = v.strip()
        if not v:
            raise ValueError("Directory name cannot be empty")
        # Check for dangerous patterns
        if any(char in v for char in ["/", "\\", "..", "\x00", "\n", "\r", "\t"]):
            raise ValueError("Directory name contains invalid characters")
        # Length limit
        if len(v) > 255:
            raise ValueError("Directory name too long (max 255 characters)")
        return v

    @field_validator("doc_type_directories")
    @classmethod
    def validate_doc_type_directories(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate doc type directories mapping."""
        if not isinstance(v, dict):
            raise ValueError("doc_type_directories must be a dictionary")
        from src.shared.security import SecurityValidator

        allowed_types = SecurityValidator.ALLOWED_DOC_TYPES
        for doc_type, dir_name in v.items():
            # Validate key is an allowed doc type
            if doc_type not in allowed_types:
                raise ValueError(
                    f"Invalid doc type: {doc_type}. Allowed: {sorted(allowed_types)}"
                )
            # Validate directory name
            if not isinstance(dir_name, str):
                raise ValueError(f"Directory name must be a string for {doc_type}")
            dir_name = dir_name.strip()
            if not dir_name:
                raise ValueError(f"Directory name cannot be empty for {doc_type}")
            # Check for dangerous patterns
            if any(
                char in dir_name for char in ["/", "\\", "..", "\x00", "\n", "\r", "\t"]
            ):
                raise ValueError(
                    f"Directory name contains invalid characters for {doc_type}"
                )
            if len(dir_name) > 255:
                raise ValueError(f"Directory name too long for {doc_type}")
        return v

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump model excluding sensitive fields.

        Args:
            **kwargs: Additional arguments for model_dump

        Returns:
            Dictionary representation excluding sensitive fields
        """
        data = super().model_dump(**kwargs)
        # Ensure tokens are never included in dump
        data.pop("github_token", None)
        data.pop("gitlab_token", None)
        return data

    def __repr__(self) -> str:
        """String representation that excludes sensitive data."""
        return (
            f"DocsRepoConfig(workspace_root={self.workspace_root!r}, "
            f"log_level={self.log_level!r}, host={self.host!r}, "
            f"port={self.port!r}, github_token={'***' if self.github_token else None}, "
            f"gitlab_token={'***' if self.gitlab_token else None})"
        )

    @classmethod
    def from_env(cls) -> "DocsRepoConfig":
        """Create configuration from environment variables."""
        base_config = super().from_env()

        config_dict = base_config.model_dump()
        config_dict["github_token"] = os.getenv("GITHUB_TOKEN")
        config_dict["gitlab_token"] = os.getenv("GITLAB_TOKEN")
        config_dict["github_api_base_url"] = os.getenv(
            "GITHUB_API_BASE_URL", "https://api.github.com"
        )
        config_dict["gitlab_api_base_url"] = os.getenv(
            "GITLAB_API_BASE_URL", "https://gitlab.com/api/v4"
        )
        config_dict["github_host"] = os.getenv("GITHUB_HOST", "github.com")
        config_dict["gitlab_host"] = os.getenv("GITLAB_HOST", "gitlab.com")
        config_dict["default_doc_type"] = os.getenv("DEFAULT_DOC_TYPE", "concept")
        config_dict["default_base_branch"] = os.getenv("DEFAULT_BASE_BRANCH", "main")
        config_dict["docs_directory"] = os.getenv("DOCS_DIRECTORY", "docs")
        config_dict["repo_mode"] = os.getenv("REPO_MODE", "same")

        # Handle retry config from environment
        retry_config = RetryConfig()
        if "API_RETRY_TOTAL" in os.environ:
            retry_config.total = int(os.getenv("API_RETRY_TOTAL", "3"))
        if "API_RETRY_BACKOFF_FACTOR" in os.environ:
            retry_config.backoff_factor = int(
                os.getenv("API_RETRY_BACKOFF_FACTOR", "1")
            )
        if "API_RETRY_STATUS_CODES" in os.environ:
            codes_str = os.getenv("API_RETRY_STATUS_CODES", "")
            retry_config.status_forcelist = [
                int(c.strip()) for c in codes_str.split(",") if c.strip()
            ]
        config_dict["api_retry"] = retry_config

        return cls(**config_dict)

    @classmethod
    def from_file(cls, config_path: Path) -> "DocsRepoConfig":
        """Load configuration from YAML or TOML file.

        Note: Tokens should be loaded from environment variables for security.
        """
        base_config = super().from_file(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        suffix = config_path.suffix.lower()
        if suffix == ".yaml" or suffix == ".yml":
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        elif suffix == ".toml":
            if tomllib is None:
                raise ValueError("TOML support requires Python 3.11+ or tomli package")
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")

        docs_repo_config = data.get("docs_repo", {})
        config_dict = base_config.model_dump()

        # Handle retry config from file
        if "api_retry" in docs_repo_config:
            retry_data = docs_repo_config["api_retry"]
            retry_config = RetryConfig(
                total=retry_data.get("total", 3),
                backoff_factor=retry_data.get("backoff_factor", 1),
                status_forcelist=retry_data.get(
                    "status_forcelist", [429, 500, 502, 503, 504]
                ),
            )
            config_dict["api_retry"] = retry_config
            # Remove from docs_repo_config to avoid double processing
            docs_repo_config = {
                k: v for k, v in docs_repo_config.items() if k != "api_retry"
            }

        # Only update keys that exist in docs_repo_config
        for key, value in docs_repo_config.items():
            if key in config_dict:
                config_dict[key] = value

        # Don't load tokens from file for security - use env vars only
        # Remove tokens from config_dict if present
        config_dict.pop("github_token", None)
        config_dict.pop("gitlab_token", None)

        return cls(**config_dict)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "DocsRepoConfig":
        """Load configuration with priority: env vars > config file > defaults."""
        # Start with defaults
        config_dict = super().load(config_path).model_dump()

        # Load docs_repo specific from file if provided (tokens ignored)
        if config_path and config_path.exists():
            suffix = config_path.suffix.lower()
            if suffix in (".yaml", ".yml"):
                with open(config_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            elif suffix == ".toml":
                if tomllib is None:
                    raise ValueError(
                        "TOML support requires Python 3.11+ or tomli package"
                    )
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
            else:
                data = {}

            docs_repo_config = data.get("docs_repo", {})

            # Handle retry config from file
            if "api_retry" in docs_repo_config:
                retry_data = docs_repo_config["api_retry"]
                retry_config = RetryConfig(
                    total=retry_data.get("total", 3),
                    backoff_factor=retry_data.get("backoff_factor", 1),
                    status_forcelist=retry_data.get(
                        "status_forcelist", [429, 500, 502, 503, 504]
                    ),
                )
                config_dict["api_retry"] = retry_config
                # Remove from docs_repo_config to avoid double processing
                docs_repo_config = {
                    k: v for k, v in docs_repo_config.items() if k != "api_retry"
                }

            # Don't load tokens from file
            for key, value in docs_repo_config.items():
                if key in config_dict and key not in ("github_token", "gitlab_token"):
                    config_dict[key] = value

        # Override with env vars if set
        if "GITHUB_TOKEN" in os.environ:
            config_dict["github_token"] = os.getenv("GITHUB_TOKEN")
        if "GITLAB_TOKEN" in os.environ:
            config_dict["gitlab_token"] = os.getenv("GITLAB_TOKEN")
        if "DEFAULT_DOC_TYPE" in os.environ:
            config_dict["default_doc_type"] = os.getenv("DEFAULT_DOC_TYPE")
        if "DEFAULT_BASE_BRANCH" in os.environ:
            config_dict["default_base_branch"] = os.getenv("DEFAULT_BASE_BRANCH")
        if "GITHUB_API_BASE_URL" in os.environ:
            config_dict["github_api_base_url"] = os.getenv("GITHUB_API_BASE_URL")
        if "GITLAB_API_BASE_URL" in os.environ:
            config_dict["gitlab_api_base_url"] = os.getenv("GITLAB_API_BASE_URL")
        if "GITHUB_HOST" in os.environ:
            config_dict["github_host"] = os.getenv("GITHUB_HOST")
        if "GITLAB_HOST" in os.environ:
            config_dict["gitlab_host"] = os.getenv("GITLAB_HOST")
        if "DOCS_DIRECTORY" in os.environ:
            config_dict["docs_directory"] = os.getenv("DOCS_DIRECTORY")
        if "REPO_MODE" in os.environ:
            config_dict["repo_mode"] = os.getenv("REPO_MODE")

        # Handle retry config from environment
        if (
            "API_RETRY_TOTAL" in os.environ
            or "API_RETRY_BACKOFF_FACTOR" in os.environ
            or "API_RETRY_STATUS_CODES" in os.environ
        ):
            retry_config = config_dict.get("api_retry", RetryConfig())
            if "API_RETRY_TOTAL" in os.environ:
                retry_config.total = int(os.getenv("API_RETRY_TOTAL", "3"))
            if "API_RETRY_BACKOFF_FACTOR" in os.environ:
                retry_config.backoff_factor = int(
                    os.getenv("API_RETRY_BACKOFF_FACTOR", "1")
                )
            if "API_RETRY_STATUS_CODES" in os.environ:
                codes_str = os.getenv("API_RETRY_STATUS_CODES", "")
                retry_config.status_forcelist = [
                    int(c.strip()) for c in codes_str.split(",") if c.strip()
                ]
            config_dict["api_retry"] = retry_config

        return cls(**config_dict)
