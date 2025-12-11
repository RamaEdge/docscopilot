"""Logging configuration for MCP servers."""

import logging
import re
import sys

from src.shared.config import ServerConfig


class CredentialFilter(logging.Filter):
    """Filter to mask sensitive information in log messages."""

    # Patterns to match sensitive data
    SENSITIVE_PATTERNS = [
        (
            re.compile(
                r"(token|password|secret|key|credential)\s*[:=]\s*([^\s,}\]]+)",
                re.IGNORECASE,
            ),
            r"\1***REDACTED***",
        ),
        (
            re.compile(
                r"(github_token|gitlab_token|api_key|auth_token)\s*[:=]\s*([^\s,}\]]+)",
                re.IGNORECASE,
            ),
            r"\1***REDACTED***",
        ),
        (
            re.compile(r"(authorization|private-token)\s*:\s*([^\s]+)", re.IGNORECASE),
            r"\1***REDACTED***",
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record to mask sensitive information.

        Args:
            record: Log record to filter

        Returns:
            True (always allow, but mask sensitive data)
        """
        if hasattr(record, "msg") and record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg

        if hasattr(record, "args") and record.args:
            args = record.args
            if isinstance(args, tuple):
                masked_args: list[object] = []
                for arg in args:
                    if isinstance(arg, str):
                        masked_arg = arg
                        for pattern, replacement in self.SENSITIVE_PATTERNS:
                            masked_arg = pattern.sub(replacement, masked_arg)
                        masked_args.append(masked_arg)
                    else:
                        masked_args.append(arg)
                record.args = tuple(masked_args)

        return True


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

    # Add credential filter to prevent logging sensitive data
    handler.addFilter(CredentialFilter())

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
