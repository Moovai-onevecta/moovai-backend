from __future__ import annotations


class LLMGenerationError(Exception):
    """Raised when an AI completion fails — a transport/API error from the
    provider, or output that couldn't be parsed as JSON at all. Distinct from
    FastAPI's response-model validation failure (the model returned parseable
    JSON that just didn't match the expected shape), which is handled
    separately in app/main.py so callers can tell the two apart.
    """

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
