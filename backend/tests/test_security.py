
import pytest

from app.utils.security import (
    SecurityValidationError,
    sanitize_text,
    validate_query,
    validate_url,
)


def test_sanitize_text_removes_control_characters():
    result = sanitize_text("hello\x00world\x07test")

    assert result == "helloworldtest"


def test_sanitize_text_normalizes_whitespace():
    result = sanitize_text("  hello    world \n test  ")

    assert result == "hello world test"


def test_validate_query_returns_clean_query():
    result = validate_query("  What is Generative AI?  ")

    assert result == "What is Generative AI?"


def test_validate_query_rejects_empty_query():
    with pytest.raises(
        SecurityValidationError,
        match="cannot be empty",
    ):
        validate_query("   ")


def test_validate_query_rejects_non_string():
    with pytest.raises(
        SecurityValidationError,
        match="must be a string",
    ):
        validate_query(123)


def test_validate_query_rejects_oversized_query():
    query = "a" * 2001

    with pytest.raises(
        SecurityValidationError,
        match="cannot exceed",
    ):
        validate_query(query)


def test_validate_url_accepts_https():
    result = validate_url(
        "https://example.com/article"
    )

    assert result == "https://example.com/article"


def test_validate_url_accepts_http():
    result = validate_url(
        "http://example.com/article"
    )

    assert result == "http://example.com/article"


def test_validate_url_rejects_empty_url():
    with pytest.raises(
        SecurityValidationError,
        match="cannot be empty",
    ):
        validate_url("")


def test_validate_url_rejects_unsafe_scheme():
    with pytest.raises(
        SecurityValidationError,
        match="Only HTTP and HTTPS",
    ):
        validate_url("javascript:alert(1)")


def test_validate_url_rejects_file_scheme():
    with pytest.raises(
        SecurityValidationError,
        match="Only HTTP and HTTPS",
    ):
        validate_url("file:///etc/passwd")


def test_validate_url_rejects_whitespace():
    with pytest.raises(
        SecurityValidationError,
        match="whitespace",
    ):
        validate_url("https://example.com/my article")