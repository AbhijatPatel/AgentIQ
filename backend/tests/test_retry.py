
import pytest

from app.utils.retry import retry_with_backoff


def test_successful_function_runs_once():
    calls = []

    @retry_with_backoff(initial_delay=0)
    def operation():
        calls.append(1)
        return "success"

    result = operation()

    assert result == "success"
    assert len(calls) == 1


def test_function_retries_after_failure():
    calls = []

    @retry_with_backoff(
        max_retries=2,
        initial_delay=0,
    )
    def operation():
        calls.append(1)

        if len(calls) < 3:
            raise RuntimeError("temporary failure")

        return "success"

    result = operation()

    assert result == "success"
    assert len(calls) == 3


def test_retry_limit_raises_exception():
    calls = []

    @retry_with_backoff(
        max_retries=2,
        initial_delay=0,
    )
    def operation():
        calls.append(1)
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        operation()

    assert len(calls) == 3


def test_zero_retries_runs_once():
    calls = []

    @retry_with_backoff(
        max_retries=0,
        initial_delay=0,
    )
    def operation():
        calls.append(1)
        raise ValueError("failure")

    with pytest.raises(ValueError, match="failure"):
        operation()

    assert len(calls) == 1


def test_invalid_max_retries():
    with pytest.raises(ValueError):
        retry_with_backoff(max_retries=-1)


def test_invalid_initial_delay():
    with pytest.raises(ValueError):
        retry_with_backoff(initial_delay=-1)


def test_invalid_backoff_factor():
    with pytest.raises(ValueError):
        retry_with_backoff(backoff_factor=0.5)