#!/bin/bash
# Health check script for DocsCopilot MCP servers
# Returns 0 if healthy, 1 if unhealthy

# Default health check port
HEALTH_PORT=${HEALTH_PORT:-8000}

# Try to connect to the health endpoint
# This assumes the server will have a /health endpoint
# Adjust based on actual MCP server implementation
if command -v curl >/dev/null 2>&1; then
    curl -f http://localhost:${HEALTH_PORT}/health >/dev/null 2>&1
    exit $?
elif command -v wget >/dev/null 2>&1; then
    wget --quiet --spider http://localhost:${HEALTH_PORT}/health >/dev/null 2>&1
    exit $?
else
    # Fallback: check if Python process is running
    pgrep -f "python.*server" >/dev/null 2>&1
    exit $?
fi


