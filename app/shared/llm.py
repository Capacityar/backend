import json
from typing import Any

import google.generativeai as genai
import groq
from groq import Groq

from app.config import settings


class LlmConfigurationError(RuntimeError):
    pass


class LlmResponseError(RuntimeError):
    pass


class LlmTimeoutError(LlmResponseError, TimeoutError):
    pass


_TIMEOUT_CLASS_NAMES = {
    "APITimeoutError",
    "TimeoutException",
    "ReadTimeout",
    "ConnectTimeout",
    "WriteTimeout",
    "PoolTimeout",
    "DeadlineExceeded",
}


def _is_timeout_exception(exc: BaseException | None) -> bool:
    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, (TimeoutError, groq.APITimeoutError)):
            return True
        if current.__class__.__name__ in _TIMEOUT_CLASS_NAMES:
            return True
        current = current.__cause__ or current.__context__
    return False


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: float | None = None,
    ) -> None:
        key = api_key or settings.gemini_api_key
        if not key:
            raise LlmConfigurationError(
                "GEMINI_API_KEY is not set; cannot instantiate GeminiClient."
            )
        genai.configure(api_key=key)
        self._model_name = model_name or settings.gemini_model
        self._timeout = timeout

    def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        effective_timeout = (
            self._timeout
            if self._timeout is not None
            else settings.llm_timeout_seconds
        )
        model = genai.GenerativeModel(self._model_name)
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": temperature,
                },
                request_options={"timeout": effective_timeout},
            )
        except Exception as exc:
            if _is_timeout_exception(exc):
                raise LlmTimeoutError(
                    f"Gemini call timed out after {effective_timeout}s: {exc}"
                ) from exc
            raise LlmResponseError(f"Gemini call failed: {exc}") from exc

        try:
            return json.loads(response.text)
        except (ValueError, AttributeError) as exc:
            raise LlmResponseError(
                f"Gemini returned a non-JSON response: {response!r}"
            ) from exc


class GroqClient:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: float | None = None,
    ) -> None:
        key = api_key or settings.groq_api_key
        if not key:
            raise LlmConfigurationError(
                "GROQ_API_KEY is not set; cannot instantiate GroqClient."
            )
        self._timeout = timeout
        effective_timeout = (
            timeout if timeout is not None else settings.llm_timeout_seconds
        )
        self._client = Groq(api_key=key, timeout=effective_timeout)
        self._model_name = model_name or settings.groq_model

    def generate_json(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        effective_timeout = (
            self._timeout
            if self._timeout is not None
            else settings.llm_timeout_seconds
        )
        schema_hint = json.dumps(response_schema, ensure_ascii=False)
        system_message = (
            "Sos un generador de JSON. Devolves UNICAMENTE un JSON valido que "
            "respete el siguiente JSON Schema, sin texto adicional ni markdown:\n"
            f"{schema_hint}"
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=effective_timeout,
            )
        except Exception as exc:
            if _is_timeout_exception(exc):
                raise LlmTimeoutError(
                    f"Groq call timed out after {effective_timeout}s: {exc}"
                ) from exc
            raise LlmResponseError(f"Groq call failed: {exc}") from exc

        if not response.choices:
            raise LlmResponseError("Groq returned no choices.")

        content = response.choices[0].message.content or ""
        try:
            return json.loads(content)
        except ValueError as exc:
            raise LlmResponseError(
                f"Groq returned a non-JSON payload: {content!r}"
            ) from exc
