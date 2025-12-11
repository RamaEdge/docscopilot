"""Unit tests for config module."""

import os
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from src.shared.config import (
    CodeContextConfig,
    DocsRepoConfig,
    RetryConfig,
    ServerConfig,
    TemplatesStyleConfig,
)


@pytest.mark.unit
class TestServerConfig:
    """Test cases for ServerConfig class."""

    def test_defaults(self):
        """Test default configuration values."""
        config = ServerConfig()
        assert config.log_level == "INFO"
        assert config.host == "0.0.0.0"
        assert config.port == 8000

    def test_from_env(self, tmp_path):
        """Test loading from environment variables."""
        with patch.dict(
            os.environ,
            {
                "WORKSPACE_ROOT": str(tmp_path),
                "LOG_LEVEL": "DEBUG",
                "HOST": "127.0.0.1",
                "PORT": "9000",
            },
        ):
            config = ServerConfig.from_env()
            assert config.workspace_root == tmp_path
            assert config.log_level == "DEBUG"
            assert config.host == "127.0.0.1"
            assert config.port == 9000

    def test_from_file_yaml(self, tmp_path):
        """Test loading from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {
                "workspace_root": str(tmp_path),
                "log_level": "WARNING",
                "host": "localhost",
                "port": 8080,
            }
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = ServerConfig.from_file(config_file)
        assert config.log_level == "WARNING"
        assert config.host == "localhost"
        assert config.port == 8080

    def test_from_file_not_found(self, tmp_path):
        """Test loading from non-existent file."""
        config_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            ServerConfig.from_file(config_file)

    def test_load_priority_env_over_file(self, tmp_path):
        """Test that environment variables override file config."""
        config_file = tmp_path / "config.yaml"
        config_data = {"server": {"log_level": "WARNING", "port": 8080}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "PORT": "9000"}):
            config = ServerConfig.load(config_file)
            assert config.log_level == "DEBUG"  # Env overrides file
            assert config.port == 9000  # Env overrides file

    def test_load_priority_file_over_defaults(self, tmp_path):
        """Test that file config overrides defaults."""
        config_file = tmp_path / "config.yaml"
        config_data = {"server": {"log_level": "WARNING", "port": 8080}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Clear env vars to test file over defaults
        with patch.dict(os.environ, {}, clear=True):
            config = ServerConfig.load(config_file)
            assert config.log_level == "WARNING"  # File overrides default
            assert config.port == 8080  # File overrides default
            assert config.host == "0.0.0.0"  # Default used


@pytest.mark.unit
class TestCodeContextConfig:
    """Test cases for CodeContextConfig class."""

    def test_from_env(self, tmp_path):
        """Test loading from environment variables."""
        with patch.dict(
            os.environ,
            {
                "WORKSPACE_ROOT": str(tmp_path),
                "GIT_BINARY": "/usr/bin/git",
                "SUPPORTED_LANGUAGES": "python,javascript,go",
            },
        ):
            config = CodeContextConfig.from_env()
            assert config.git_binary == "/usr/bin/git"
            assert "python" in config.supported_languages
            assert "javascript" in config.supported_languages
            assert "go" in config.supported_languages

    def test_from_file_yaml(self, tmp_path):
        """Test loading from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "code_context": {
                "git_binary": "/usr/bin/git",
                "supported_languages": ["python", "javascript"],
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = CodeContextConfig.from_file(config_file)
        assert config.git_binary == "/usr/bin/git"
        assert config.supported_languages == ["python", "javascript"]

    def test_from_file_yaml_string_languages(self, tmp_path):
        """Test loading languages as comma-separated string."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "code_context": {
                "supported_languages": "python,javascript,go",
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = CodeContextConfig.from_file(config_file)
        assert isinstance(config.supported_languages, list)
        assert "python" in config.supported_languages

    def test_load_priority(self, tmp_path):
        """Test configuration priority."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "code_context": {
                "git_binary": "/usr/bin/git",
                "supported_languages": ["python"],
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(os.environ, {"GIT_BINARY": "/custom/git"}):
            config = CodeContextConfig.load(config_file)
            assert config.git_binary == "/custom/git"  # Env overrides file


@pytest.mark.unit
class TestTemplatesStyleConfig:
    """Test cases for TemplatesStyleConfig class."""

    def test_from_env(self, tmp_path):
        """Test loading from environment variables."""
        templates_path = tmp_path / "templates"
        templates_path.mkdir()

        with patch.dict(
            os.environ, {"DOCSCOPILOT_TEMPLATES_PATH": str(templates_path)}
        ):
            config = TemplatesStyleConfig.from_env()
            assert config.templates_path == templates_path

    def test_from_file_yaml(self, tmp_path):
        """Test loading from YAML file."""
        templates_path = tmp_path / "templates"
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "templates_style": {"templates_path": str(templates_path)},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = TemplatesStyleConfig.from_file(config_file)
        assert config.templates_path == templates_path

    def test_load_priority(self, tmp_path):
        """Test configuration priority."""
        templates_path = tmp_path / "templates"
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "templates_style": {"templates_path": str(tmp_path / "file_templates")},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(
            os.environ, {"DOCSCOPILOT_TEMPLATES_PATH": str(templates_path)}
        ):
            config = TemplatesStyleConfig.load(config_file)
            assert config.templates_path == templates_path  # Env overrides file


@pytest.mark.unit
class TestRetryConfig:
    """Test cases for RetryConfig class."""

    def test_defaults(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        assert config.total == 3
        assert config.backoff_factor == 1
        assert config.status_forcelist == [429, 500, 502, 503, 504]

    def test_validate_total_valid(self):
        """Test valid total values."""
        assert RetryConfig(total=0).total == 0
        assert RetryConfig(total=5).total == 5
        assert RetryConfig(total=10).total == 10

    def test_validate_total_invalid(self):
        """Test invalid total values."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(total=-1)
        assert "cannot be negative" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(total=11)
        assert "cannot exceed 10" in str(exc_info.value)

    def test_validate_backoff_factor_valid(self):
        """Test valid backoff factor values."""
        assert RetryConfig(backoff_factor=0).backoff_factor == 0
        assert RetryConfig(backoff_factor=5).backoff_factor == 5
        assert RetryConfig(backoff_factor=10).backoff_factor == 10

    def test_validate_backoff_factor_invalid(self):
        """Test invalid backoff factor values."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(backoff_factor=-1)
        assert "cannot be negative" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(backoff_factor=11)
        assert "cannot exceed 10" in str(exc_info.value)

    def test_validate_status_codes_valid(self):
        """Test valid status code lists."""
        config = RetryConfig(status_forcelist=[429, 500, 502])
        assert config.status_forcelist == [429, 500, 502]

        # Test deduplication and sorting
        config = RetryConfig(status_forcelist=[500, 429, 500, 502])
        assert config.status_forcelist == [429, 500, 502]

    def test_validate_status_codes_invalid(self):
        """Test invalid status code lists."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(status_forcelist=[99])
        assert "Invalid HTTP status code" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(status_forcelist=[600])
        assert "Invalid HTTP status code" in str(exc_info.value)

        # Pydantic validates types before our validator runs
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(status_forcelist=["not_an_int"])
        # Pydantic will raise a type validation error before our validator runs
        assert "valid integer" in str(exc_info.value) or "Input should be" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestServerConfigTimeouts:
    """Test cases for ServerConfig timeout validation."""

    def test_validate_timeout_valid(self):
        """Test valid timeout values."""
        config = ServerConfig(git_command_timeout=1, api_request_timeout=60)
        assert config.git_command_timeout == 1
        assert config.api_request_timeout == 60

    def test_validate_timeout_invalid(self):
        """Test invalid timeout values."""
        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(git_command_timeout=0)
        assert "must be at least 1 second" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ServerConfig(api_request_timeout=3601)
        assert "cannot exceed 3600 seconds" in str(exc_info.value)


@pytest.mark.unit
class TestDocsRepoConfig:
    """Test cases for DocsRepoConfig class."""

    def test_from_env(self, tmp_path):
        """Test loading from environment variables."""
        with patch.dict(
            os.environ,
            {
                "WORKSPACE_ROOT": str(tmp_path),
                "GITHUB_TOKEN": "github_token_value",
                "GITLAB_TOKEN": "gitlab_token_value",
            },
        ):
            config = DocsRepoConfig.from_env()
            assert config.github_token == "github_token_value"
            assert config.gitlab_token == "gitlab_token_value"

    def test_from_file_ignores_tokens(self, tmp_path):
        """Test that tokens in config file are ignored for security."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "server": {"workspace_root": str(tmp_path)},
            "docs_repo": {
                "github_token": "file_token",
                "gitlab_token": "file_token",
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = DocsRepoConfig.from_file(config_file)
        # Tokens should not be loaded from file
        assert config.github_token is None
        assert config.gitlab_token is None

    def test_load_priority_env_tokens(self, tmp_path):
        """Test that env tokens override file config."""
        config_file = tmp_path / "config.yaml"
        config_data = {"server": {"workspace_root": str(tmp_path)}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with patch.dict(
            os.environ,
            {"GITHUB_TOKEN": "env_token", "GITLAB_TOKEN": "env_token"},
        ):
            config = DocsRepoConfig.load(config_file)
            assert config.github_token == "env_token"
            assert config.gitlab_token == "env_token"
