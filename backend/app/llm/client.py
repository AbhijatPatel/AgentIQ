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

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

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
        api_key = settings.effective_llm_api_key
        if not api_key:
            logger.warning(
                "No LLM API key configured (neither OPENAI_API_KEY nor GROQ_API_KEY). "
                "LLM calls will fail until configured."
            )

        client_kwargs = {
            "api_key": api_key or "missing_key",
            "timeout": float(settings.LLM_TIMEOUT_SECONDS),
            "max_retries": 0,
        }

        base_url = settings.LLM_BASE_URL.strip() if settings.LLM_BASE_URL else ""
        if not base_url:
            if api_key.startswith("gsk_"):
                base_url = "https://api.groq.com/openai/v1"
            elif api_key.startswith("sk-or-"):
                base_url = "https://openrouter.ai/api/v1"
            else:
                base_url = "https://api.openai.com/v1"

        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)
        self._base_url = base_url
        
        # Provider-aware model normalization
        is_groq = "groq" in base_url.lower() or api_key.startswith("gsk_")
        is_openai = "api.openai.com" in base_url.lower() and not is_groq

        model = (settings.LLM_MODEL or "").strip()
        fallback_model = (settings.LLM_FALLBACK_MODEL or "").strip()

        if is_groq:
            if not model or model.startswith("openai/"):
                model = "llama-3.3-70b-versatile"
            if not fallback_model or fallback_model.startswith("openai/"):
                fallback_model = "llama-3.1-8b-instant"
        elif is_openai:
            if not model or "llama" in model.lower() or model.startswith("openai/"):
                model = "gpt-4o-mini"
            if not fallback_model or "llama" in fallback_model.lower() or fallback_model.startswith("openai/"):
                fallback_model = "gpt-3.5-turbo"

        self._model = model or "llama-3.3-70b-versatile"
        self._fallback_model = fallback_model or "llama-3.1-8b-instant"
        self._temperature = settings.LLM_TEMPERATURE

        provider_name = "Groq" if is_groq else ("OpenAI" if is_openai else "Custom/OpenRouter")
        logger.info(
            "LLMClient initialized (provider=%s, primary_model=%s, fallback_model=%s, base_url=%s)",
            provider_name,
            self._model,
            self._fallback_model,
            base_url,
        )

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
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Generate a text response from the LLM with automatic retry and model fallback.
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
                        if settings.LLM_MIN_REQUEST_DELAY_SECONDS > 0:
                            time.sleep(settings.LLM_MIN_REQUEST_DELAY_SECONDS)

                        request_kwargs = {
                            "model": current_model,
                            "messages": messages,
                            "temperature": (
                                temperature
                                if temperature is not None
                                else self._temperature
                            ),
                            "max_tokens": (
                                settings.LLM_JSON_MAX_OUTPUT_TOKENS
                                if response_format is not None
                                else settings.LLM_MAX_OUTPUT_TOKENS
                            ),
                        }

                        if response_format is not None:
                            request_kwargs["response_format"] = response_format

                        response = self._client.chat.completions.create(
                            **request_kwargs
                        )

                    content = response.choices[0].message.content
                    if content is None:
                        raise LLMClientError("LLM returned an empty response.")

                    logger.info(
                        "LLM request successful using model=%s",
                        current_model,
                    )
                    return content.strip()

                except AuthenticationError as exc:
                    # Permanent credential error - fail fast immediately
                    logger.error(
                        "LLM authentication failed for model=%s. Please verify the API key.",
                        current_model,
                    )
                    raise LLMClientError("LLM authentication failed. Please verify the API key.") from exc

                except RateLimitError as exc:
                    last_error = exc
                    if self._is_daily_token_limit(exc):
                        if current_model != models_to_try[-1]:
                            logger.warning(
                                "Daily token quota reached for model=%s. Switching to fallback model=%s.",
                                current_model,
                                self._fallback_model,
                            )
                            break
                        raise LLMClientError(
                            "All configured LLM models have reached their daily token quota. Please try again later."
                        ) from exc

                    if attempt >= settings.LLM_MAX_RETRIES:
                        logger.error(
                            "LLM rate limit persisted for model=%s after %s retries.",
                            current_model,
                            settings.LLM_MAX_RETRIES,
                        )
                        if current_model != models_to_try[-1]:
                            logger.warning(
                                "Switching from model=%s to fallback model=%s.",
                                current_model,
                                self._fallback_model,
                            )
                            break
                        raise LLMClientError(
                            "LLM rate limit persisted after automatic retries. Please try again later."
                        ) from exc

                    retry_after = self._get_retry_after(exc)
                    delay = min(retry_after, settings.LLM_RATE_LIMIT_MAX_DELAY_SECONDS) if retry_after is not None else self._calculate_retry_delay(attempt)
                    logger.warning(
                        "LLM rate limit hit for model=%s. Retry %s/%s in %.2f seconds.",
                        current_model,
                        attempt + 1,
                        settings.LLM_MAX_RETRIES,
                        delay,
                    )
                    time.sleep(delay)

                except (APIConnectionError, APITimeoutError, InternalServerError) as exc:
                    last_error = exc
                    error_type = type(exc).__name__
                    logger.warning(
                        "LLM transient error (%s) for model=%s on attempt %d/%d",
                        error_type,
                        current_model,
                        attempt + 1,
                        settings.LLM_MAX_RETRIES + 1,
                    )

                    if attempt < settings.LLM_MAX_RETRIES:
                        delay = self._calculate_retry_delay(attempt)
                        logger.info("Retrying LLM request in %.2f seconds...", delay)
                        time.sleep(delay)
                    else:
                        if current_model != models_to_try[-1]:
                            logger.warning(
                                "Model %s failed with %s after %d retries. Switching to fallback model=%s.",
                                current_model,
                                error_type,
                                settings.LLM_MAX_RETRIES,
                                self._fallback_model,
                            )
                            break
                        raise LLMClientError(
                            f"The AI service is temporarily unreachable ({error_type}). Please try again."
                        ) from exc

                except APIError as exc:
                    last_error = exc
                    status_code = getattr(exc, "status_code", None)
                    message = getattr(exc, "message", str(exc))
                    logger.error(
                        "LLM API error (status=%s, type=%s, model=%s): %s",
                        status_code,
                        type(exc).__name__,
                        current_model,
                        message,
                    )
                    # For 5xx server errors, retry with backoff
                    if status_code and status_code >= 500 and attempt < settings.LLM_MAX_RETRIES:
                        delay = self._calculate_retry_delay(attempt)
                        logger.info("Retrying LLM request in %.2f seconds...", delay)
                        time.sleep(delay)
                    else:
                        # For 4xx errors (e.g. 400 Bad Request, 404 Model Not Found),
                        # break to try fallback model immediately instead of retrying invalid request
                        if current_model != models_to_try[-1]:
                            logger.warning(
                                "Model %s failed with API error (status=%s). Trying fallback model=%s.",
                                current_model,
                                status_code,
                                self._fallback_model,
                            )
                            break
                        safe_msg = f"AI service error ({status_code or type(exc).__name__}): {message}" if status_code else "The AI service returned an error. Please try again."
                        raise LLMClientError(safe_msg) from exc

                except LLMClientError:
                    raise

                except Exception as exc:
                    last_error = exc
                    logger.error(
                        "Unexpected error calling LLM (model=%s, type=%s): %s",
                        current_model,
                        type(exc).__name__,
                        exc,
                    )
                    if current_model != models_to_try[-1]:
                        logger.warning(
                            "Model %s failed with %s. Trying fallback model=%s.",
                            current_model,
                            type(exc).__name__,
                            self._fallback_model,
                        )
                        break
                    raise LLMClientError(f"Unexpected error communicating with AI service: {exc}") from exc

        if last_error:
            raise LLMClientError(f"All configured LLM models failed: {last_error}") from last_error

        raise LLMClientError("LLM request failed unexpectedly.")

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
            response_format={"type": "json_object"},
        )

        def parse_response(raw_response: str) -> dict[str, Any]:
            cleaned = raw_response.strip()

            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "", 1)
                cleaned = cleaned.replace("```", "", 1)
                cleaned = cleaned.strip()

            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                start = cleaned.find("{")
                end = cleaned.rfind("}")

                if start == -1 or end == -1 or end <= start:
                    raise

                parsed = json.loads(cleaned[start:end + 1])

            if not isinstance(parsed, dict):
                raise LLMClientError(
                    "LLM JSON response must be an object."
                )

            return parsed

        try:
            data = parse_response(response)
        except json.JSONDecodeError as exc:
            logger.warning(
                "LLM returned invalid JSON; requesting one corrected response."
            )

            repair_prompt = f"""
The previous response was not valid JSON. Return ONLY a corrected JSON object
that satisfies the original request. Do not include Markdown, explanations,
or extra text.

Original request:
{prompt}

Previous response:
{response}
""".strip()

            try:
                repaired_response = self.generate(
                    prompt=repair_prompt,
                    system=system,
                    temperature=temperature,
                    model=model,
                    response_format={"type": "json_object"},
                )
                data = parse_response(repaired_response)
            except (LLMClientError, json.JSONDecodeError) as repair_exc:
                logger.error(
                    "LLM returned invalid JSON: %s",
                    response,
                )
                raise LLMClientError(
                    "LLM returned invalid JSON."
                ) from repair_exc

        return data

llm_client = LLMClient()