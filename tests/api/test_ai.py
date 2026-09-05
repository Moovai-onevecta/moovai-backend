"""Tests for app.api.routes.ai.

The AIService itself is stubbed via dependency_overrides — these tests are
about HTTP wiring/schemas, not about OpenAI's actual output quality (see
tests/services/test_ai.py for the REST-call-shape test against AIService).
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.ai import router
from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import (
    get_ai_service,
    get_chat_history_service,
    get_itinerary_service,
)
from app.exceptions import LLMGenerationError
from app.main import handle_llm_generation_error
from app.models.ai import ChatResponse
from app.models.itinerary import Itinerary


@pytest.fixture
def mock_ai() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(uid="user-1", email="dave@example.com")


@pytest.fixture
def mock_itinerary_service(current_user: AuthenticatedUser) -> MagicMock:
    service = MagicMock()
    service.get_model.return_value = Itinerary(
        id="itin-1",
        name="Ghana Trip",
        owner_uid=current_user.uid,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 10),
    )
    return service


@pytest.fixture
def mock_chat_history_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    mock_ai: AsyncMock,
    current_user: AuthenticatedUser,
    mock_itinerary_service: MagicMock,
    mock_chat_history_service: MagicMock,
) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(LLMGenerationError, handle_llm_generation_error)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_ai_service] = lambda: mock_ai
    app.dependency_overrides[get_itinerary_service] = lambda: mock_itinerary_service
    app.dependency_overrides[get_chat_history_service] = lambda: (
        mock_chat_history_service
    )
    return TestClient(app)


class TestChat:
    def test_returns_reply_from_ai_service(
        self, client: TestClient, mock_ai: AsyncMock
    ) -> None:
        mock_ai.chat.return_value = ChatResponse(
            reply="Hi there!", model="gpt-3.5-turbo"
        )

        response = client.post(
            "/ai/chat", json={"messages": [{"role": "user", "content": "hi"}]}
        )

        assert response.status_code == 200
        assert response.json() == {"reply": "Hi there!", "model": "gpt-3.5-turbo"}

    def test_requires_at_least_one_message(self, client: TestClient) -> None:
        response = client.post("/ai/chat", json={"messages": []})
        assert response.status_code == 422


class TestChatAssistant:
    def test_returns_reply_and_suggested_actions(
        self, client: TestClient, mock_ai: AsyncMock
    ) -> None:
        mock_ai.complete_json.return_value = {
            "reply": "Elmina fits well after Cape Coast.",
            "suggested_actions": [
                {
                    "id": "add-elmina",
                    "kind": "add_stop",
                    "title": "Add Elmina as a stop",
                    "city": "Elmina",
                    "blurb": "30 min from Cape Coast.",
                    "est": "Est. half day",
                    "price": {"amount": 34, "currency": "USD", "is_estimate": True},
                }
            ],
        }

        response = client.post(
            "/ai/chat/assistant",
            json={
                "itinerary_id": "itin-1",
                "messages": [{"role": "user", "content": "What about Elmina?"}],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["reply"] == "Elmina fits well after Cape Coast."
        assert body["suggested_actions"][0]["kind"] == "add_stop"
        mock_ai.complete_json.assert_awaited_once()

    def test_returns_502_when_model_output_is_malformed(
        self, client: TestClient, mock_ai: AsyncMock
    ) -> None:
        mock_ai.complete_json.return_value = {"reply": 12345}  # wrong type, no coercion

        response = client.post(
            "/ai/chat/assistant",
            json={
                "itinerary_id": "itin-1",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

        assert response.status_code == 502
        assert response.json()["error"]["code"] == "LLM_GENERATION_FAILED"

    def test_returns_404_when_itinerary_not_owned(
        self, client: TestClient, mock_itinerary_service: MagicMock
    ) -> None:
        mock_itinerary_service.get_model.return_value = None

        response = client.post(
            "/ai/chat/assistant",
            json={
                "itinerary_id": "itin-1",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

        assert response.status_code == 404

    def test_persists_messages_and_actions_to_chat_history(
        self,
        client: TestClient,
        mock_ai: AsyncMock,
        mock_chat_history_service: MagicMock,
    ) -> None:
        mock_ai.complete_json.return_value = {
            "reply": "Elmina fits well after Cape Coast.",
            "suggested_actions": [
                {
                    "id": "add-elmina",
                    "kind": "add_stop",
                    "title": "Add Elmina as a stop",
                    "city": "Elmina",
                    "blurb": "30 min from Cape Coast.",
                    "est": "Est. half day",
                    "price": {"amount": 34, "currency": "USD", "is_estimate": True},
                }
            ],
        }

        response = client.post(
            "/ai/chat/assistant",
            json={
                "itinerary_id": "itin-1",
                "messages": [{"role": "user", "content": "What about Elmina?"}],
            },
        )

        assert response.status_code == 200
        mock_chat_history_service.append_messages.assert_called_once()
        messages_args = mock_chat_history_service.append_messages.call_args[0]
        assert messages_args[0] == "itin-1"
        assert messages_args[1] == "user-1"
        assert [m.role for m in messages_args[2]] == ["user", "assistant"]

        mock_chat_history_service.append_actions.assert_called_once()
        actions_args = mock_chat_history_service.append_actions.call_args[0]
        assert actions_args[2][0].action_id == "add-elmina"


class TestGetChatHistory:
    def test_returns_404_when_itinerary_not_owned(
        self, client: TestClient, mock_itinerary_service: MagicMock
    ) -> None:
        mock_itinerary_service.get_model.return_value = None

        response = client.get("/ai/chat/itin-1/history")

        assert response.status_code == 404

    def test_returns_404_when_no_history_yet(
        self, client: TestClient, mock_chat_history_service: MagicMock
    ) -> None:
        mock_chat_history_service.get_for_itinerary.return_value = None

        response = client.get("/ai/chat/itin-1/history")

        assert response.status_code == 404


class TestResolveChatAction:
    def test_returns_404_when_itinerary_not_owned(
        self, client: TestClient, mock_itinerary_service: MagicMock
    ) -> None:
        mock_itinerary_service.get_model.return_value = None

        response = client.post(
            "/ai/chat/itin-1/actions/add-elmina/resolve", json={"accepted": True}
        )

        assert response.status_code == 404

    def test_calls_resolve_action_with_accepted_flag(
        self, client: TestClient, mock_chat_history_service: MagicMock
    ) -> None:
        from app.models.chat_history import ChatHistory

        mock_chat_history_service.resolve_action.return_value = ChatHistory(
            itinerary_id="itin-1", owner_uid="user-1"
        )

        response = client.post(
            "/ai/chat/itin-1/actions/add-elmina/resolve", json={"accepted": True}
        )

        assert response.status_code == 200
        mock_chat_history_service.resolve_action.assert_called_once_with(
            "itin-1", "add-elmina", True
        )


class TestSuggestDestinations:
    def test_returns_suggestions(self, client: TestClient, mock_ai: AsyncMock) -> None:
        mock_ai.complete_json.return_value = {
            "suggestions": [
                {
                    "city": "Accra",
                    "country": "Ghana",
                    "why": "Matches your interest in street food and history.",
                    "best_months": ["November", "December"],
                    "estimated_daily_budget": {
                        "amount": 60,
                        "currency": "USD",
                        "is_estimate": True,
                    },
                }
            ]
        }

        response = client.post(
            "/ai/destinations/suggest",
            json={"brief": "history and street food, budget trip"},
        )

        assert response.status_code == 200
        assert response.json()["suggestions"][0]["city"] == "Accra"


class TestSuggestQuestions:
    def test_returns_empty_list_for_unambiguous_brief(
        self, client: TestClient, mock_ai: AsyncMock
    ) -> None:
        mock_ai.complete_json.return_value = {"questions": []}

        response = client.post(
            "/ai/questions/suggest",
            json={"brief": "6 days in Ghana, $800 budget, love street food"},
        )

        assert response.status_code == 200
        assert response.json() == {"questions": []}


class TestGenerateItinerary:
    def test_returns_options(self, client: TestClient, mock_ai: AsyncMock) -> None:
        mock_ai.complete_json.return_value = {
            "options": [
                {
                    "letter": "A",
                    "name": "Ghana Highlights",
                    "is_ai_pick": True,
                    "summary": "A balanced first trip to Ghana.",
                    "total_cost": {
                        "amount": 780,
                        "currency": "USD",
                        "is_estimate": True,
                    },
                    "days": [
                        {
                            "day_number": 1,
                            "city": "Accra",
                            "date": "2026-11-12",
                            "activities": [
                                {
                                    "title": "Jamestown walk",
                                    "est": "Est. 3 hrs",
                                    "price": {
                                        "amount": 34,
                                        "currency": "USD",
                                        "is_estimate": True,
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        response = client.post(
            "/ai/itineraries/generate",
            json={"brief": "6 days in Ghana, love street food and history"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["options"][0]["letter"] == "A"
        assert body["options"][0]["is_ai_pick"] is True
