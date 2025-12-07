# Containerfile for DocsCopilot MCP Servers
# Built for Podman (rootless mode supported)

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml ./

# Install the package
RUN pip install --no-cache-dir -e .

# Copy container scripts
COPY container/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY container/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Create non-root user for rootless Podman support
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose default MCP server port (adjust per server)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1

# Entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

