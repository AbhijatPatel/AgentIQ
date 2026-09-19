"""
Centralized LLM client.

All AgentIQ agents use this client for LLM calls.

Features:
- Centralized OpenAI-compatible client
- Configurable primary and fallback models
- Rate-limit retry with exponential backoff
- Automatic fallback on daily token quota exhaustion
- Retry-After header support
- Random jitter
- Concurrency control
- Minimum request delay
- Timeout handling
- Consistent error handling
- JSON response helper
"""

from __future__ import annotations

import json
import random
import time
from threading import Semaphore
from typing import Any, Optional

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from app.config.settings import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)


class LLMClientError(Exception):
    """Raised when an LLM call fails or returns unusable data."""


class LLMClient:
    """
    Centralized LLM client used by Planner, Researcher, Writer and Critic.
    """

    _semaphore = Semaphore(settings.LLM_CONCURRENCY_LIMIT)

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY is not set. "
                "LLM calls will fail until you add it to your .env file."
            )

        client_kwargs = {
            "api_key": settings.OPENAI_API_KEY,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
            "max_retries": 0,
        }

        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL

        self._client = OpenAI(**client_kwargs)

        self._model = settings.LLM_MODEL
        self._fallback_model = settings.LLM_FALLBACK_MODEL
        self._temperature = settings.LLM_TEMPERATURE

    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        """

        delay = min(
            settings.LLM_RETRY_BASE_DELAY_SECONDS * (2**attempt),
            settings.LLM_RATE_LIMIT_MAX_DELAY_SECONDS,
        )

        jitter = random.uniform(0, delay * 0.25)

        return delay + jitter

    def _get_retry_after(
        self,
        exc: RateLimitError,
    ) -> float | None:
        """
        Read Retry-After header when provided by the provider.
        """

        response = getattr(exc, "response", None)

        if response is None:
            return None

        headers = getattr(response, "headers", None)

        if not headers:
            return None

        retry_after_header = headers.get("retry-after")

        if not retry_after_header:
            return None

        try:
            retry_after = float(retry_after_header)
        except (TypeError, ValueError):
            return None

        if retry_after < 0:
            return None

        return retry_after

    def _is_daily_token_limit(
        self,
        exc: RateLimitError,
    ) -> bool:
        """
        Detect provider-side daily token quota errors.

        These errors should not waste time retrying the same model.
        """

        error_text = str(exc).lower()

        return (
            "tokens per day" in error_text
            or "tpd" in error_text
            or "daily token" in error_text
            or "token per day" in error_text
        )

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Generate a text response from the LLM.

        Model selection:

        1. Requested model / primary model
        2. Fallback model if the primary hits a rate limit
        3. Automatic retries for temporary rate limits
        """

        messages = []

        if system:
            messages.append(
                {
                    "role": "system",
                    "content": system,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        requested_model = model or self._model

        models_to_try = [requested_model]

        # Only automatically use fallback when the caller is
        # using the configured primary model.
        if (
            requested_model == self._model
            and self._fallback_model
            and self._fallback_model != self._model
        ):
            models_to_try.append(self._fallback_model)

        last_error: Exception | None = None

        for current_model in models_to_try:

            for attempt in range(settings.LLM_MAX_RETRIES + 1):

                try:
                    logger.debug(
                        "LLM request attempt %s/%s using model=%s",
                        attempt + 1,
                        settings.LLM_MAX_RETRIES + 1,
                        current_model,
                    )

                    with self._semaphore:

                        time.sleep(
                            settings.LLM_MIN_REQUEST_DELAY_SECONDS
                        )

                        response = (
                            self._client.chat.completions.create(
                                model=current_model,
                                messages=messages,
                                temperature=(
                                    temperature
                                    if temperature is not None
                                    else self._temperature
                                ),
                                max_tokens=(
                                    settings.LLM_MAX_OUTPUT_TOKENS
                                ),
                            )
                        )

                    content = response.choices[0].message.content

                    if content is None:
                        raise LLMClientError(
                            "LLM returned an empty response."
                        )

                    logger.info(
                        "LLM request successful using model=%s",
                        current_model,
                    )

                    return content.strip()

                except RateLimitError as exc:

                    last_error = exc

                    # -------------------------------------------------
                    # DAILY TOKEN QUOTA
                    # -------------------------------------------------
                    #
                    # Do NOT retry the exhausted model.
                    # Immediately switch to fallback.
                    #
                    if self._is_daily_token_limit(exc):

                        if current_model != models_to_try[-1]:

                            logger.warning(
                                "Daily token quota reached for "
                                "model=%s. Switching to fallback "
                                "model=%s.",
                                current_model,
                                self._fallback_model,
                            )

                            break

                        logger.error(
                            "Daily token quota also reached for "
                            "fallback model=%s.",
                            current_model,
                        )

                        raise LLMClientError(
                            "All configured LLM models have reached "
                            "their daily token quota. "
                            "Please try again later."
                        ) from exc

                    # -------------------------------------------------
                    # TEMPORARY RATE LIMIT
                    # -------------------------------------------------

                    if attempt >= settings.LLM_MAX_RETRIES:

                        logger.error(
                            "LLM rate limit persisted for "
                            "model=%s after %s retries.",
                            current_model,
                            settings.LLM_MAX_RETRIES,
                        )

                        # Try fallback before giving up.
                        if current_model != models_to_try[-1]:

                            logger.warning(
                                "Switching from model=%s to "
                                "fallback model=%s.",
                                current_model,
                                self._fallback_model,
                            )

                            break

                        raise LLMClientError(
                            "LLM rate limit persisted after "
                            "automatic retries. "
                            "Please try again later."
                        ) from exc

                    retry_after = self._get_retry_after(exc)

                    if retry_after is not None:

                        delay = min(
                            retry_after,
                            settings.LLM_RATE_LIMIT_MAX_DELAY_SECONDS,
                        )

                    else:

                        delay = self._calculate_retry_delay(
                            attempt
                        )

                    logger.warning(
                        "LLM rate limit hit for model=%s. "
                        "Retry %s/%s in %.2f seconds.",
                        current_model,
                        attempt + 1,
                        settings.LLM_MAX_RETRIES,
                        delay,
                    )

                    time.sleep(delay)

                except APITimeoutError as exc:

                    logger.error(
                        "LLM call timed out using model=%s: %s",
                        current_model,
                        exc,
                    )

                    raise LLMClientError(
                        "The LLM request timed out. "
                        "Please try again."
                    ) from exc

                except APIError as exc:

                    logger.error(
                        "LLM API error using model=%s: %s",
                        current_model,
                        exc,
                    )

                    raise LLMClientError(
                        f"LLM API error: {exc}"
                    ) from exc

                except LLMClientError:

                    raise

                except Exception as exc:

                    logger.error(
                        "Unexpected error calling LLM "
                        "using model=%s: %s",
                        current_model,
                        exc,
                    )

                    raise LLMClientError(
                        f"Unexpected error calling LLM: {exc}"
                    ) from exc

        if last_error:

            raise LLMClientError(
                "All configured LLM models failed."
            ) from last_error

        raise LLMClientError(
            "LLM request failed unexpectedly."
        )

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate and parse a JSON response.
        """

        json_prompt = f"""
Return ONLY valid JSON.

Do not include:
- Markdown
- Code fences
- Explanations
- Extra text

Keep the JSON concise.

User request:

{prompt}
""".strip()

        response = self.generate(
            prompt=json_prompt,
            system=system,
            temperature=temperature,
            model=model,
        )

        cleaned = response.strip()

        if cleaned.startswith("```"):

            cleaned = cleaned.replace(
                "```json",
                "",
                1,
            )

            cleaned = cleaned.replace(
                "```",
                "",
                1,
            )

            cleaned = cleaned.strip()

        try:

            data = json.loads(cleaned)

        except json.JSONDecodeError as exc:

            logger.error(
                "LLM returned invalid JSON: %s",
                response,
            )

            raise LLMClientError(
                "LLM returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):

            raise LLMClientError(
                "LLM JSON response must be an object."
            )

        return data


llm_client = LLMClient()