"""
Tests for the centralized LLM client.

These tests do NOT call the real OpenAI API (that would cost money and
be flaky in CI). Instead, we mock the OpenAI client so we can verify
our error-handling and JSON-parsing logic works correctly.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.llm.client import LLMClient, LLMClientError


def _make_mock_response(content: str):
    """Helper to build a fake OpenAI response object."""
    mock_message = MagicMock()
    mock_message.content = content

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


@patch("app.llm.client.OpenAI")
def test_generate_returns_text(mock_openai_class):
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = _make_mock_response(
        "Hello, world!"
    )
    mock_openai_class.return_value = mock_client_instance

    client = LLMClient()
    result = client.generate("Say hello")

    assert result == "Hello, world!"


@patch("app.llm.client.OpenAI")
def test_generate_json_parses_valid_json(mock_openai_class):
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = _make_mock_response(
        '{"greeting": "hello"}'
    )
    mock_openai_class.return_value = mock_client_instance

    client = LLMClient()
    result = client.generate_json("Return a greeting")

    assert result == {"greeting": "hello"}


@patch("app.llm.client.OpenAI")
def test_generate_json_strips_markdown_fences(mock_openai_class):
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = _make_mock_response(
        '```json\n{"greeting": "hello"}\n```'
    )
    mock_openai_class.return_value = mock_client_instance

    client = LLMClient()
    result = client.generate_json("Return a greeting")

    assert result == {"greeting": "hello"}


@patch("app.llm.client.OpenAI")
def test_generate_json_raises_on_invalid_json(mock_openai_class):
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = _make_mock_response(
        "this is not json"
    )
    mock_openai_class.return_value = mock_client_instance

    client = LLMClient()
    with pytest.raises(LLMClientError):
        client.generate_json("Return a greeting")


@patch("app.llm.client.OpenAI")
def test_generate_raises_on_empty_response(mock_openai_class):
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = _make_mock_response(None)
    mock_openai_class.return_value = mock_client_instance

    client = LLMClient()
    with pytest.raises(LLMClientError):
        client.generate("Say hello")