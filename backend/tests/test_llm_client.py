from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.llm.client import LLMClient, LLMClientError


def create_rate_limit_error(message: str) -> RateLimitError:
    """
    Create a mock OpenAI rate-limit error.
    """

    response = MagicMock()

    response.status_code = 429

    response.headers = {}

    return RateLimitError(
        message,
        response=response,
        body={
            "error": {
                "message": message,
            }
        },
    )


def create_success_response(content: str):
    """
    Create a mock successful OpenAI response.
    """

    return MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=content
                )
            )
        ]
    )


def test_daily_token_limit_switches_to_fallback():
    """
    Verify that a daily token quota error on the primary
    model immediately switches to the fallback model.
    """

    client = LLMClient()

    primary_model = "primary-model"
    fallback_model = "fallback-model"

    client._model = primary_model
    client._fallback_model = fallback_model

    mock_create = MagicMock(
        side_effect=[
            create_rate_limit_error(
                "tokens per day (TPD): "
                "Limit 200000, "
                "Used 199128, "
                "Requested 1565."
            ),
            create_success_response(
                "FALLBACK_SUCCESS"
            ),
        ]
    )

    client._client.chat.completions.create = mock_create

    result = client.generate(
        prompt="Reply with exactly: FALLBACK_SUCCESS"
    )

    assert result == "FALLBACK_SUCCESS"

    assert mock_create.call_count == 2

    first_call = mock_create.call_args_list[0]
    second_call = mock_create.call_args_list[1]

    assert first_call.kwargs["model"] == primary_model

    assert second_call.kwargs["model"] == fallback_model


def test_fallback_model_can_generate_successfully():
    """
    Verify that an explicitly selected fallback model
    can return a successful response.
    """

    client = LLMClient()

    fallback_model = "fallback-model"

    client._model = "primary-model"
    client._fallback_model = fallback_model

    mock_create = MagicMock(
        return_value=create_success_response(
            "DIRECT_FALLBACK_SUCCESS"
        )
    )

    client._client.chat.completions.create = mock_create

    result = client.generate(
        prompt="Reply with exactly: DIRECT_FALLBACK_SUCCESS",
        model=fallback_model,
    )

    assert result == "DIRECT_FALLBACK_SUCCESS"

    assert mock_create.call_count == 1

    assert (
        mock_create.call_args.kwargs["model"]
        == fallback_model
    )


def test_daily_token_limit_detection():
    """
    Verify that daily token quota errors are detected correctly.
    """

    client = LLMClient()

    error = create_rate_limit_error(
        "tokens per day (TPD): "
        "Limit 200000, "
        "Used 199128, "
        "Requested 1565."
    )

    assert client._is_daily_token_limit(error) is True


def test_normal_rate_limit_is_not_daily_quota():
    """
    Verify that a normal temporary rate limit is not treated
    as a daily token quota error.
    """

    client = LLMClient()

    error = create_rate_limit_error(
        "Rate limit reached. Please try again later."
    )

    assert client._is_daily_token_limit(error) is False


def test_generate_json_repairs_malformed_response():
    client = LLMClient()

    with patch.object(
        client,
        "generate",
        side_effect=[
            "Here is the result: {not valid JSON}",
            '{"evidence": []}',
        ],
    ) as mock_generate:
        result = client.generate_json("Return evidence")

    assert result == {"evidence": []}
    assert mock_generate.call_count == 2


def test_generate_json_raises_when_repair_fails():
    client = LLMClient()

    with patch.object(
        client,
        "generate",
        side_effect=["not JSON", "still not JSON"],
    ):
        with pytest.raises(LLMClientError, match="invalid JSON"):
            client.generate_json("Return evidence")


def test_generate_json_uses_structured_output_budget():
    client = LLMClient()
    mock_create = MagicMock(
        return_value=create_success_response('{"ok": true}')
    )
    client._client.chat.completions.create = mock_create

    assert client.generate_json("Return an object") == {"ok": True}

    request = mock_create.call_args.kwargs
    assert request["response_format"] == {"type": "json_object"}
    assert request["max_tokens"] == 8192


def test_connection_error_retries_and_succeeds():
    """Verify that transient APIConnectionError is retried and succeeds."""
    from openai import APIConnectionError
    import httpx

    client = LLMClient()
    client._model = "primary-model"
    client._fallback_model = "fallback-model"

    mock_request = MagicMock(spec=httpx.Request)
    mock_create = MagicMock(
        side_effect=[
            APIConnectionError(request=mock_request, message="Connection failed"),
            create_success_response("RETRY_CONNECTION_SUCCESS"),
        ]
    )
    client._client.chat.completions.create = mock_create

    with patch("time.sleep"):
        result = client.generate("Hello")

    assert result == "RETRY_CONNECTION_SUCCESS"
    assert mock_create.call_count == 2


def test_connection_error_falls_back_to_secondary_model():
    """Verify that when primary model connection fails completely, fallback model is tried."""
    from openai import APIConnectionError
    import httpx

    client = LLMClient()
    client._model = "primary-model"
    client._fallback_model = "fallback-model"

    mock_request = MagicMock(spec=httpx.Request)
    mock_create = MagicMock(
        side_effect=[
            APIConnectionError(request=mock_request, message="Connection error attempt 1"),
            APIConnectionError(request=mock_request, message="Connection error attempt 2"),
            APIConnectionError(request=mock_request, message="Connection error attempt 3"),
            create_success_response("FALLBACK_RECOVERY"),
        ]
    )
    client._client.chat.completions.create = mock_create

    with patch("time.sleep"):
        result = client.generate("Hello")

    assert result == "FALLBACK_RECOVERY"
    assert mock_create.call_count == 4


def test_auth_error_fails_fast_without_retries():
    """Verify that AuthenticationError fails immediately on attempt 1 without retry."""
    from openai import AuthenticationError
    import httpx

    client = LLMClient()
    client._model = "primary-model"

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.headers = {}
    mock_create = MagicMock(
        side_effect=AuthenticationError("Invalid API Key", response=mock_response, body={"error": "Invalid API Key"})
    )
    client._client.chat.completions.create = mock_create

    with pytest.raises(LLMClientError, match="authentication failed"):
        client.generate("Hello")

    assert mock_create.call_count == 1