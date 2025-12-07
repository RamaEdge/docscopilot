# Configuration Guide

DocsCopilot MCP servers support multiple configuration methods with a clear priority order:

1. **Environment Variables** (highest priority)
2. **Configuration Files** (YAML or TOML)
3. **Default Values** (lowest priority)

## Configuration Priority

When a setting is specified in multiple places, the priority order is:
1. Environment variables override everything
2. Configuration file values override defaults
3. Default values are used if not specified elsewhere

## Configuration Methods

### Environment Variables

All configuration can be set via environment variables. This is the recommended method for sensitive data like API tokens.

```bash
export WORKSPACE_ROOT=/workspace
export LOG_LEVEL=INFO
export GITHUB_TOKEN=your_token_here
export DOCSCOPILOT_TEMPLATES_PATH=/path/to/templates
```

### Configuration Files

Configuration files can be in YAML (`.yaml` or `.yml`) or TOML (`.toml`) format.

#### Supported File Locations

The configuration file is loaded from:
1. Path specified via `DOCSCOPILOT_CONFIG` environment variable
2. `docscopilot.yaml` or `docscopilot.toml` in the current working directory
3. `~/.config/docscopilot/docscopilot.yaml` or `~/.config/docscopilot/docscopilot.toml`

#### Example YAML Configuration

See `config/docscopilot.yaml.example` for a complete example.

```yaml
server:
  workspace_root: /workspace
  log_level: INFO
  host: 0.0.0.0
  port: 8000

code_context:
  git_binary: git
  supported_languages:
    - python
    - javascript

templates_style:
  templates_path: /path/to/templates

docs_repo:
  # Tokens should be set via environment variables
```

#### Example TOML Configuration

See `config/docscopilot.toml.example` for a complete example.

```toml
[server]
workspace_root = "/workspace"
log_level = "INFO"
host = "0.0.0.0"
port = 8000

[code_context]
git_binary = "git"
supported_languages = ["python", "javascript"]

[templates_style]
templates_path = "/path/to/templates"
```

## Configuration Options

### Server Configuration

Common settings for all MCP servers:

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `workspace_root` | `WORKSPACE_ROOT` | Current directory | Root directory containing repositories |
| `log_level` | `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `host` | `HOST` | `0.0.0.0` | Server host address |
| `port` | `PORT` | `8000` | Server port |

### Code Context Server

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `git_binary` | `GIT_BINARY` | `git` | Path to git executable |
| `supported_languages` | `SUPPORTED_LANGUAGES` | `python` | Comma-separated list of supported languages |

### Templates + Style Server

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `templates_path` | `DOCSCOPILOT_TEMPLATES_PATH` | `None` | Optional path to external templates repository |

### Docs Repo Server

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `github_token` | `GITHUB_TOKEN` | `None` | GitHub personal access token (set via env var for security) |
| `gitlab_token` | `GITLAB_TOKEN` | `None` | GitLab personal access token (set via env var for security) |

## Security Best Practices

1. **Never commit tokens to configuration files** - Always use environment variables for sensitive data
2. **Use environment variables in production** - More secure and easier to manage
3. **Restrict file permissions** - If using configuration files, ensure proper file permissions (`chmod 600`)
4. **Use secrets management** - In production, use secrets management systems (e.g., Kubernetes secrets, AWS Secrets Manager)

## Configuration Validation

All configuration is validated on startup using Pydantic models. Invalid values will cause the server to fail with a clear error message.

### Common Validation Errors

- **Invalid path**: Ensure `workspace_root` and `templates_path` point to existing directories
- **Invalid port**: Port must be between 1 and 65535
- **Invalid log level**: Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Missing required fields**: All required fields must be provided

## Examples

### Minimal Configuration (Defaults Only)

```python
from src.shared.config import CodeContextConfig

# Uses all defaults
config = CodeContextConfig()
```

### Environment Variables Only

```bash
export WORKSPACE_ROOT=/workspace
export LOG_LEVEL=DEBUG
export SUPPORTED_LANGUAGES=python,javascript,go
```

```python
from src.shared.config import CodeContextConfig

config = CodeContextConfig.from_env()
```

### Configuration File

```python
from pathlib import Path
from src.shared.config import CodeContextConfig

config_path = Path("docscopilot.yaml")
config = CodeContextConfig.from_file(config_path)
```

### Combined (Recommended)

```python
from pathlib import Path
from src.shared.config import CodeContextConfig

# Automatically loads from file, then applies env vars
config_path = Path("docscopilot.yaml")
config = CodeContextConfig.load(config_path)
```

## Troubleshooting

### Configuration Not Loading

1. Check file path and permissions
2. Verify file format (YAML/TOML syntax)
3. Check environment variable names (case-sensitive)
4. Review server logs for validation errors

### Environment Variables Not Overriding File Config

Ensure you're using the `.load()` method which respects the priority order:

```python
config = CodeContextConfig.load(config_path)  # Correct
# Not: config = CodeContextConfig.from_file(config_path)  # Ignores env vars
```

