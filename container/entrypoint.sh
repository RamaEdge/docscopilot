#!/bin/bash
# Entrypoint script for DocsCopilot MCP servers
# Supports rootless Podman mode

set -e

# Default server name
SERVER_NAME=${SERVER_NAME:-mcp-server}

# Log startup
echo "Starting DocsCopilot MCP Server: ${SERVER_NAME}"
echo "Working directory: $(pwd)"
echo "User: $(whoami)"
echo "Python version: $(python3 --version)"

# Check if workspace is mounted
if [ ! -d "${WORKSPACE_ROOT:-/workspace}" ]; then
    echo "Warning: Workspace directory ${WORKSPACE_ROOT:-/workspace} not found"
fi

# Start the appropriate MCP server based on SERVER_NAME
case "${SERVER_NAME}" in
    code-context)
        echo "Starting Code Context MCP Server..."
        exec python3 -m src.code_context_server.server
        ;;
    templates-style)
        echo "Starting Templates + Style MCP Server..."
        exec python3 -m src.templates_style_server.server
        ;;
    docs-repo)
        echo "Starting Docs Repo MCP Server..."
        exec python3 -m src.docs_repo_server.server
        ;;
    *)
        echo "Error: Unknown SERVER_NAME: ${SERVER_NAME}"
        echo "Valid options: code-context, templates-style, docs-repo"
        exit 1
        ;;
esac

