from unittest.mock import MagicMock

from openai import RateLimitError

from app.llm.client import LLMClient


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