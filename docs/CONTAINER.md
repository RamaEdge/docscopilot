# Container Configuration

This document describes how to build and run DocsCopilot MCP servers using Podman containers.

## Files

The `container/` directory contains:
- `entrypoint.sh` - Entrypoint script that starts the appropriate MCP server based on `SERVER_NAME` environment variable
- `healthcheck.sh` - Health check script for container health monitoring
- `config.env.example` - Example environment configuration file

## Environment Variables

### Common Variables

- `SERVER_NAME` - Which MCP server to run: `code-context`, `templates-style`, or `docs-repo`
- `WORKSPACE_ROOT` - Path to workspace directory (default: `/workspace`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `PORT` - Server port (default: `8000`)
- `HOST` - Server host (default: `0.0.0.0`)

### Code Context Server

- `GIT_BINARY` - Path to git binary (default: `git`)
- `SUPPORTED_LANGUAGES` - Comma-separated list of supported languages (default: `python`)

### Templates + Style Server

- `DOCSCOPILOT_TEMPLATES_PATH` - Path to templates directory (default: workspace `.docscopilot`)

### Docs Repo Server

- `GITHUB_TOKEN` - GitHub personal access token (optional)
- `GITLAB_TOKEN` - GitLab personal access token (optional)

## Rootless Podman Support

The containers are configured to run as a non-root user (UID 1000) to support rootless Podman mode. This ensures:

- Containers can run without root privileges
- Better security isolation
- Compatibility with Podman rootless mode

## Usage

### Building Containers

```bash
podman-compose build
```

### Running Containers

```bash
podman-compose up -d
```

### Viewing Logs

```bash
podman-compose logs -f <service-name>
```

### Stopping Containers

```bash
podman-compose stop
```

## Health Checks

Each container includes a health check that runs every 30 seconds. The health check script (`healthcheck.sh`) verifies that the MCP server is responding correctly.

## Networking

All containers are connected to a bridge network (`docscopilot-network`) allowing them to communicate with each other.

## Volumes

- `./src:/app/src:ro` - Source code (read-only)
- `./workspace:/workspace` - Workspace directory (read-only for code-context and templates-style, read-write for docs-repo)

## Ports

- Code Context Server: `8001`
- Templates + Style Server: `8002`
- Docs Repo Server: `8003`

Each server exposes port 8000 internally, mapped to different host ports.

