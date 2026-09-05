"""Tests for app.api.routes.search — HTTP wiring only, SearchService stubbed."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.search import router
from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import get_search_service
from app.models.search import FlightResult, HotelResult


@pytest.fixture
def mock_search() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(mock_search: AsyncMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid="user-1")
    app.dependency_overrides[get_search_service] = lambda: mock_search
    return TestClient(app)


class TestSearchFlights:
    def test_returns_results_from_search_service(
        self, client: TestClient, mock_search: AsyncMock
    ) -> None:
        mock_search.search_flights.return_value = [
            FlightResult(id="flt_1", price=61.0, stops=0)
        ]

        response = client.post(
            "/search/flights",
            json={
                "departure_id": "ACC",
                "arrival_id": "KMS",
                "outbound_date": "2026-11-14",
            },
        )

        assert response.status_code == 200
        assert response.json()["results"][0]["id"] == "flt_1"
        mock_search.search_flights.assert_awaited_once_with(
            departure_id="ACC",
            arrival_id="KMS",
            outbound_date="2026-11-14",
            return_date=None,
            adults=1,
        )


class TestSearchHotels:
    def test_returns_results_from_search_service(
        self, client: TestClient, mock_search: AsyncMock
    ) -> None:
        mock_search.search_hotels.return_value = [
            HotelResult(name="Four Villages Inn", rate_per_night=54.0)
        ]

        response = client.post(
            "/search/hotels",
            json={
                "location": "Kumasi",
                "check_in_date": "2026-11-14",
                "check_out_date": "2026-11-16",
            },
        )

        assert response.status_code == 200
        assert response.json()["results"][0]["name"] == "Four Villages Inn"
