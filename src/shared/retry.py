"""Retry logic for external API calls."""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from src.shared.errors import APIError, ErrorCode
from src.shared.logging import setup_logging

logger = setup_logging()

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying function calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Factor to multiply delay by on each retry
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )

            # If we get here, all retries failed
            if last_exception:
                raise APIError(
                    f"Failed after {max_retries + 1} attempts: {str(last_exception)}",
                    details=f"Function: {func.__name__}, Last error: {type(last_exception).__name__}",
                    error_code=ErrorCode.API_REQUEST_FAILED,
                ) from last_exception

            # Should never reach here, but for type checking
            raise APIError(
                "Retry logic failed unexpectedly",
                error_code=ErrorCode.API_REQUEST_FAILED,
            )

        return wrapper

    return decorator
