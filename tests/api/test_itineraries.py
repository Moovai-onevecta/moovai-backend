"""Tests for app.api.routes.itineraries.

Auth and the Firestore-backed service are both stubbed via FastAPI
dependency_overrides — these tests are about HTTP status codes, request
validation, and ownership enforcement, not about Firestore itself (that's
covered in tests/services/test_itineraries.py and test_base.py).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.itineraries import router
from app.core.deps.auth import AuthenticatedUser, get_current_user
from app.core.deps.services import get_itinerary_service
from app.models.itinerary import Itinerary


def sample_itinerary(**overrides: Any) -> Itinerary:
    defaults: dict[str, Any] = {
        "id": "itin-1",
        "name": "Ghana Trip",
        "owner_uid": "user-1",
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 10),
    }
    defaults.update(overrides)
    return Itinerary(**defaults)


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(uid="user-1", email="dave@example.com")


@pytest.fixture
def client(mock_service: MagicMock, current_user: AuthenticatedUser) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_itinerary_service] = lambda: mock_service
    return TestClient(app)


class TestCreateItinerary:
    def test_sets_owner_uid_from_authenticated_user(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.create.return_value = sample_itinerary()

        response = client.post(
            "/itineraries",
            json={
                "name": "Ghana Trip",
                "start_date": "2026-06-01",
                "end_date": "2026-06-10",
            },
        )

        assert response.status_code == 201
        created_arg = mock_service.create.call_args[0][0]
        assert created_arg.owner_uid == "user-1"
        assert response.json()["owner_uid"] == "user-1"

    def test_rejects_client_supplied_owner_uid(self, client: TestClient) -> None:
        response = client.post(
            "/itineraries",
            json={
                "name": "Ghana Trip",
                "start_date": "2026-06-01",
                "end_date": "2026-06-10",
                "owner_uid": "someone-else",
            },
        )

        assert response.status_code == 422


class TestListMyItineraries:
    def test_lists_only_current_users_itineraries(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.list_for_owner.return_value = [sample_itinerary()]

        response = client.get("/itineraries")

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_service.list_for_owner.assert_called_once_with("user-1")


class TestGetItinerary:
    def test_returns_404_when_missing(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = None

        response = client.get("/itineraries/nonexistent")

        assert response.status_code == 404

    def test_returns_404_when_not_owner(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary(owner_uid="someone-else")

        response = client.get("/itineraries/itin-1")

        # 404, not 403 — avoid confirming to a non-owner that the resource exists.
        assert response.status_code == 404

    def test_returns_itinerary_for_owner(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary()

        response = client.get("/itineraries/itin-1")

        assert response.status_code == 200
        assert response.json()["id"] == "itin-1"


class TestUpdateItinerary:
    def test_returns_404_when_missing(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = None

        response = client.patch("/itineraries/nonexistent", json={"name": "New Name"})

        assert response.status_code == 404

    def test_returns_404_when_not_owner(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary(owner_uid="someone-else")

        response = client.patch("/itineraries/itin-1", json={"name": "New Name"})

        assert response.status_code == 404

    def test_passes_only_provided_fields_to_service(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary()
        mock_service.update.return_value = sample_itinerary(name="New Name")

        response = client.patch("/itineraries/itin-1", json={"name": "New Name"})

        assert response.status_code == 200
        mock_service.update.assert_called_once_with("itin-1", {"name": "New Name"})


class TestDeleteItinerary:
    def test_returns_404_when_missing(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = None

        response = client.delete("/itineraries/nonexistent")

        assert response.status_code == 404

    def test_returns_404_when_not_owner(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary(owner_uid="someone-else")

        response = client.delete("/itineraries/itin-1")

        assert response.status_code == 404

    def test_deletes_for_owner(
        self, client: TestClient, mock_service: MagicMock
    ) -> None:
        mock_service.get_model.return_value = sample_itinerary()

        response = client.delete("/itineraries/itin-1")

        assert response.status_code == 204
        mock_service.delete_document.assert_called_once_with("itin-1")
