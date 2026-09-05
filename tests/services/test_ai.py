"""Tests for app.services.ai.AIService.

Verifies the actual HTTP request AIService builds against OpenAI's Chat
Completions REST API (no `openai` SDK involved) using httpx's MockTransport,
so no network access or real API key is needed to run this suite.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.exceptions import LLMGenerationError
from app.models.ai import ChatMessage, ChatRequest
from app.services.ai import AIService


def make_settings() -> Settings:
    return Settings(
        firebase_project_id="test-project",
        openai_api_key="sk-test-123",
        openai_model="gpt-3.5-turbo",
        serpapi_api_key="test-key",
    )


def openai_response(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


class _CapturingTransport(httpx.MockTransport):
    """A MockTransport that records the last request it handled."""

    def __init__(self, handler: Any) -> None:
        self.last_request: httpx.Request | None = None

        def wrapped(request: httpx.Request) -> httpx.Response:
            self.last_request = request
            return handler(request)

        super().__init__(wrapped)


def install_fake_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Any
) -> _CapturingTransport:
    """Redirects every httpx.AsyncClient created inside AIService to `handler`."""
    transport = _CapturingTransport(handler)
    real_client_cls = httpx.AsyncClient

    def fake_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)
    return transport


class TestChat:
    @pytest.mark.asyncio
    async def test_posts_to_openai_chat_completions_with_bearer_auth(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        transport = install_fake_transport(
            monkeypatch,
            lambda request: httpx.Response(200, json=openai_response("hello!")),
        )

        ai = AIService(make_settings())
        request = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
        result = await ai.chat(request)

        assert result.reply == "hello!"
        assert result.model == "gpt-3.5-turbo"

        sent = transport.last_request
        assert sent is not None
        assert str(sent.url) == "https://api.openai.com/v1/chat/completions"
        assert sent.headers["authorization"] == "Bearer sk-test-123"
        body = json.loads(sent.content)
        assert body["model"] == "gpt-3.5-turbo"
        assert body["messages"] == [{"role": "user", "content": "hi"}]


class TestCompleteJson:
    @pytest.mark.asyncio
    async def test_requests_json_object_response_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        transport = install_fake_transport(
            monkeypatch,
            lambda request: httpx.Response(
                200, json=openai_response('{"reply": "ok"}')
            ),
        )

        ai = AIService(make_settings())
        result = await ai.complete_json("system prompt", {"brief": "a trip"})

        assert result == {"reply": "ok"}
        sent = transport.last_request
        assert sent is not None
        body = json.loads(sent.content)
        assert body["response_format"] == {"type": "json_object"}
        assert body["messages"][0] == {"role": "system", "content": "system prompt"}
        assert json.loads(body["messages"][1]["content"]) == {"brief": "a trip"}

    @pytest.mark.asyncio
    async def test_tolerates_markdown_fenced_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_transport(
            monkeypatch,
            lambda request: httpx.Response(
                200, json=openai_response('```json\n{"reply": "ok"}\n```')
            ),
        )

        ai = AIService(make_settings())
        result = await ai.complete_json("system prompt", "a trip")

        assert result == {"reply": "ok"}

    @pytest.mark.asyncio
    async def test_wraps_transport_errors_as_llm_generation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_fake_transport(
            monkeypatch, lambda request: httpx.Response(500, text="boom")
        )

        ai = AIService(make_settings())
        with pytest.raises(LLMGenerationError):
            await ai.complete_json("system prompt", "a trip")
