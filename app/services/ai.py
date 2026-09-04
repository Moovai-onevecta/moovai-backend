import httpx

from app.core.config import Settings
from app.models.ai import ChatRequest, ChatResponse

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AIService:
    """Thin client over a hosted LLM API. We never load or run models locally."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model

    async def chat(self, request: ChatRequest) -> ChatResponse:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": self._model,
            "max_tokens": request.max_tokens,
            "messages": [msg.model_dump() for msg in request.messages],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(_ANTHROPIC_API_URL, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        reply = "".join(
            block["text"] for block in data.get("content", []) if block.get("type") == "text"
        )
        return ChatResponse(reply=reply, model=self._model)
