"""Groq LLM adapter with an optional fallback model and safe error mapping."""

from collections.abc import Iterator

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger("insurio.llm")


class GroqLLM:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.model_name = settings.GROQ_MODEL
        self._fallback = settings.GROQ_FALLBACK_MODEL.strip() or None
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self._settings.GROQ_API_KEY.strip())

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
            except ImportError as exc:
                raise AppError(
                    "The AI client library is not installed.",
                    code="llm_unavailable",
                    status_code=503,
                ) from exc
            self._client = Groq(
                api_key=self._settings.GROQ_API_KEY,
                timeout=self._settings.GROQ_TIMEOUT_SECONDS,
                max_retries=1,
            )
        return self._client

    def _models(self) -> list[str]:
        models = [self.model_name]
        if self._fallback and self._fallback != self.model_name:
            models.append(self._fallback)
        return models

    def _create(self, messages: list[dict[str, str]], *, stream: bool, json_mode: bool):
        kwargs: dict[str, object] = {
            "messages": messages,
            "temperature": self._settings.LLM_TEMPERATURE,
            "max_tokens": self._settings.LLM_MAX_TOKENS,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        for model in self._models():
            try:
                return self._get_client().chat.completions.create(
                    model=model, stream=stream, **kwargs
                )
            except Exception as exc:  # provider errors are mapped, never leaked
                last_error = exc
                logger.warning(
                    "llm_request_failed",
                    extra={"event": "llm_request_failed", "status_code": None},
                )
        raise AppError(
            "The AI provider could not be reached. Please try again shortly.",
            code="llm_unavailable",
            status_code=502,
        ) from last_error

    def complete(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        response = self._create(messages, stream=False, json_mode=json_mode)
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise AppError("The AI provider returned an empty response.", code="llm_empty")
        content = choices[0].message.content or ""
        if not content.strip():
            raise AppError("The AI provider returned an empty response.", code="llm_empty")
        return content

    def stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        emitted = False
        last_error: Exception | None = None
        for model in self._models():
            try:
                stream = self._get_client().chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self._settings.LLM_TEMPERATURE,
                    max_tokens=self._settings.LLM_MAX_TOKENS,
                    stream=True,
                )
                for chunk in stream:
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    delta = getattr(choices[0].delta, "content", None)
                    if delta:
                        emitted = True
                        yield delta
                return
            except GeneratorExit:
                raise
            except Exception as exc:
                last_error = exc
                if emitted:
                    raise AppError(
                        "The answer stream was interrupted. Please retry.",
                        code="llm_stream_interrupted",
                        status_code=502,
                    ) from exc
                logger.warning("llm_stream_failed", extra={"event": "llm_stream_failed"})
        raise AppError(
            "The AI provider could not be reached. Please try again shortly.",
            code="llm_unavailable",
            status_code=502,
        ) from last_error
