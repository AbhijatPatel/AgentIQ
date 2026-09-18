
"""
Reusable retry utilities for temporary failures.

Provides controlled retries with exponential backoff so external
API and network operations can recover from temporary failures.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from app.utils.logger import get_logger


logger = get_logger(__name__)


T = TypeVar("T")


DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0
DEFAULT_BACKOFF_FACTOR = 2.0


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """
    Retry a function when one of the specified exceptions occurs.

    Retry delays use exponential backoff:

        attempt 1 → initial delay
        attempt 2 → initial delay × backoff factor
        attempt 3 → previous delay × backoff factor

    The original exception is raised after all retries are exhausted.
    """

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")

    if initial_delay < 0:
        raise ValueError("initial_delay cannot be negative")

    if backoff_factor < 1:
        raise ValueError("backoff_factor must be at least 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            delay = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)

                except exceptions as exc:
                    if attempt >= max_retries:
                        logger.error(
                            f"Retry limit reached for {func.__name__}: "
                            f"{exc}"
                        )
                        raise

                    attempt += 1

                    logger.warning(
                        f"{func.__name__} failed "
                        f"(attempt {attempt}/{max_retries + 1}): "
                        f"{exc}. Retrying in {delay:.2f}s"
                    )

                    if delay > 0:
                        time.sleep(delay)

                    delay *= backoff_factor

        return wrapper

    return decorator
