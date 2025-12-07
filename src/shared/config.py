"""Configuration management for MCP servers."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]
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

        config_dict = base_config.model_dump()
        config_dict["github_token"] = os.getenv("GITHUB_TOKEN")
        config_dict["gitlab_token"] = os.getenv("GITLAB_TOKEN")
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
            # Don't load tokens from file
            for key, value in docs_repo_config.items():
                if key in config_dict and key not in ("github_token", "gitlab_token"):
                    config_dict[key] = value

        # Override with env vars if set
        if "GITHUB_TOKEN" in os.environ:
            config_dict["github_token"] = os.getenv("GITHUB_TOKEN")
        if "GITLAB_TOKEN" in os.environ:
            config_dict["gitlab_token"] = os.getenv("GITLAB_TOKEN")

        return cls(**config_dict)
