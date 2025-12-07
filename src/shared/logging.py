"""Logging configuration for MCP servers."""

import logging
import sys

from src.shared.config import ServerConfig


def setup_logging(config: ServerConfig | None = None) -> logging.Logger:
    """Set up structured logging for MCP servers.

    Args:
        config: Server configuration. If None, uses defaults.

    Returns:
        Configured logger instance.
    """
    log_level = getattr(config, "log_level", "INFO") if config else "INFO"

    # Create logger
    logger = logging.getLogger("docscopilot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
