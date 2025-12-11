"""Performance metrics and timing utilities."""

import asyncio
import functools
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from src.shared.logging import setup_logging

logger = setup_logging()

# Global metrics storage
_metrics: dict[str, list[float]] = defaultdict(list)


def get_metrics() -> dict[str, dict[str, float]]:
    """Get aggregated performance metrics.

    Returns:
        Dictionary with metric names and their statistics (count, avg, min, max)
    """
    result: dict[str, dict[str, float]] = {}
    for name, times in _metrics.items():
        if times:
            result[name] = {
                "count": len(times),
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
            }
    return result


def reset_metrics() -> None:
    """Reset all performance metrics."""
    _metrics.clear()


def track_performance(
    operation_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to track performance of operations.

    Args:
        operation_name: Name of the operation being tracked

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                _metrics[operation_name].append(elapsed)
                if elapsed > 1.0:  # Log slow operations (>1s)
                    logger.warning(f"Slow operation '{operation_name}': {elapsed:.3f}s")
                else:
                    logger.debug(f"Operation '{operation_name}': {elapsed:.3f}s")

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                _metrics[operation_name].append(elapsed)
                if elapsed > 1.0:  # Log slow operations (>1s)
                    logger.warning(f"Slow operation '{operation_name}': {elapsed:.3f}s")
                else:
                    logger.debug(f"Operation '{operation_name}': {elapsed:.3f}s")

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def time_operation(
    operation_name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Context manager for timing operations.

    This is an alias for track_performance for backward compatibility.
    """
    return track_performance(operation_name)
