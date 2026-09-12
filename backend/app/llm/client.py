"""
Centralized LLM client.

Why this file exists:
Every agent (Planner, Researcher, Writer, Critic) needs to call the LLM.
Instead of each agent creating its own OpenAI client and repeating
error-handling / timeout logic, they all call through this one module.

If we ever swap providers (e.g. OpenAI -> Anthropic), we only change
this file - no agent code needs to change.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClientError(Exception):
    """Raised when the LLM call fails after retries, or returns something unusable."""


class LLMClient:
    """
    Thin wrapper around the OpenAI API.

    Usage:
        from app.llm.client import llm_client

        text = llm_client.generate("Say hello")

        data = llm_client.generate_json(
            "Return a JSON object with a 'greeting' field"
        )
    """

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY is not set. LLM calls will fail until "
                "you add it to your .env file."
            )

                # The OpenAI SDK reads the timeout in seconds directly.
        # base_url lets us point at Groq (or any OpenAI-compatible provider)
        # instead of OpenAI's own servers, without changing any other code.
        client_kwargs = {
            "api_key": settings.OPENAI_API_KEY,
            "timeout": settings.LLM_TIMEOUT_SECONDS,
            "max_retries": settings.LLM_MAX_RETRIES,
        }
        if settings.LLM_BASE_URL:
            client_kwargs["base_url"] = settings.LLM_BASE_URL

        self._client = OpenAI(**client_kwargs)
        self._model = settings.LLM_MODEL
        self._temperature = settings.LLM_TEMPERATURE

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Send a prompt to the LLM and return the plain text response.

        Args:
            prompt: The user-facing instruction/question.
            system: Optional system prompt (role definition, rules).
            temperature: Optional override of default temperature.
            model: Optional override of default model.

        Returns:
            The model's text response.

        Raises:
            LLMClientError: if the API call fails for any reason.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat.completions.create(
                model=model or self._model,
                messages=messages,
                temperature=temperature if temperature is not None else self._temperature,
            )
        except APITimeoutError as exc:
            logger.error(f"LLM call timed out: {exc}")
            raise LLMClientError("The LLM request timed out. Please try again.") from exc
        except RateLimitError as exc:
            logger.error(f"LLM rate limit hit: {exc}")
            raise LLMClientError("LLM rate limit reached. Please wait and retry.") from exc
        except APIError as exc:
            logger.error(f"LLM API error: {exc}")
            raise LLMClientError(f"LLM API error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - we want to catch anything unexpected here
            logger.error(f"Unexpected error calling LLM: {exc}")
            raise LLMClientError(f"Unexpected error calling LLM: {exc}") from exc

        content = response.choices[0].message.content
        if content is None:
            raise LLMClientError("LLM returned an empty response.")

        return content.strip()

    def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Same as generate(), but instructs the model to return JSON and
        parses it into a Python dict.

        This is what Planner / Researcher / Writer / Critic will use,
        since they all need structured output rather than free text.

        Raises:
            LLMClientError: if the call fails OR if the response is not valid JSON.
        """
        json_system = (
            (system + "\n\n" if system else "")
            + "You must respond with ONLY valid JSON. "
            "Do not include markdown code fences, explanations, or any text "
            "outside the JSON object."
        )

        raw_text = self.generate(
            prompt=prompt,
            system=json_system,
            temperature=temperature,
            model=model,
        )

        # Defensive cleanup: sometimes models wrap JSON in ```json fences
        # even when told not to. Strip those if present.
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(f"LLM returned invalid JSON: {raw_text}")
            raise LLMClientError(
                "LLM returned a response that was not valid JSON."
            ) from exc


# Single shared instance imported by all agents.
llm_client = LLMClient()