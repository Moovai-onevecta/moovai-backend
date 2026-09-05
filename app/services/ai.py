from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings
from app.exceptions import LLMGenerationError
from app.models.ai import ChatRequest, ChatResponse
from app.services.json_utils import parse_json_object

_OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class AIService:
    """Thin REST client over OpenAI's Chat Completions API. We call the
    hosted API directly over HTTPS — no `openai` SDK, no model hosted or run
    locally.
    """

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Plain conversational reply — no structured output required."""
        data = await self._complete(
            messages=[msg.model_dump() for msg in request.messages],
            max_tokens=request.max_tokens,
        )
        reply = data["choices"][0]["message"]["content"] or ""
        return ChatResponse(reply=reply, model=self._model)

    async def complete_json(
        self, system_prompt: str, user_content: dict[str, Any] | str
    ) -> dict[str, Any]:
        """Run one strict-JSON completion and return the parsed object.

        Used by every structured AI feature (itinerary generation, question
        suggestion, destination suggestion, chat assistant actions) — the
        system prompt describes the exact JSON shape, `response_format`
        constrains the model to a JSON object, and `parse_json_object` is a
        tolerant fallback for the rare case a model still wraps it in a
        markdown fence.
        """
        content = (
            user_content if isinstance(user_content, str) else json.dumps(user_content)
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]
        try:
            data = await self._complete(
                messages=messages,
                response_format={"type": "json_object"},
            )
            text = data["choices"][0]["message"]["content"] or ""
            return parse_json_object(text)
        except LLMGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001 - transport/parse errors wrapped below
            raise LLMGenerationError(
                "Failed to generate AI response", str(exc)
            ) from exc

    async def _complete(
        self,
        *,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {"model": self._model, "messages": messages}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if response_format is not None:
            body["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                _OPENAI_CHAT_COMPLETIONS_URL, headers=headers, json=body
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
