"""Tests for app.services.itineraries.ItineraryService.

Deliberately thin: the heavy lifting (codec, id_field, query_models) is
already covered in tests/services/test_base.py. This file just proves the
service is wired to the right collection and delegates correctly.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.itinerary import Itinerary
from app.services.itineraries import ItineraryService


@pytest.fixture
def mock_collection() -> MagicMock:
    return MagicMock(name="collection")


@pytest.fixture
def service(mock_collection: MagicMock) -> ItineraryService:
    provider = MagicMock()
    db = MagicMock()
    db.collection.return_value = mock_collection
    provider.firestore_client.return_value = db
    return ItineraryService(provider)


def test_collection_name_is_itineraries(service: ItineraryService) -> None:
    assert service.collection_name == "itineraries"


def test_id_field_is_configured(service: ItineraryService) -> None:
    assert service.id_field == "id"


def test_list_for_owner_queries_by_owner_uid(
    service: ItineraryService, mock_collection: MagicMock
) -> None:
    snapshot = MagicMock()
    snapshot.id = "itin-1"
    snapshot.to_dict.return_value = {
        "name": "Ghana Trip",
        "ownerUid": "user-1",
        "startDate": "2026-06-01",
        "endDate": "2026-06-10",
    }
    mock_collection.where.return_value.stream.return_value = [snapshot]

    results = service.list_for_owner("user-1")

    assert results == [
        Itinerary(
            id="itin-1",
            name="Ghana Trip",
            owner_uid="user-1",
            start_date="2026-06-01",
            end_date="2026-06-10",
        )
    ]


def test_create_stamps_created_and_updated_at(
    service: ItineraryService, mock_collection: MagicMock
) -> None:
    doc_ref = MagicMock()
    doc_ref.id = "itin-new"
    mock_collection.document.return_value = doc_ref
    itinerary = Itinerary(
        name="Ghana Trip",
        owner_uid="user-1",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 10),
    )

    result = service.create(itinerary)

    assert result.id == "itin-new"
    assert result.created_at is not None
    assert result.updated_at == result.created_at


def test_update_merges_changes_and_revalidates(
    service: ItineraryService, mock_collection: MagicMock
) -> None:
    snapshot = MagicMock()
    snapshot.id = "itin-1"
    snapshot.to_dict.return_value = {
        "name": "Old Name",
        "ownerUid": "user-1",
        "startDate": "2026-06-01",
        "endDate": "2026-06-10",
    }
    mock_collection.document.return_value.get.return_value = snapshot

    result = service.update("itin-1", {"name": "New Name"})

    assert result is not None
    assert result.name == "New Name"
    assert result.updated_at is not None
    mock_collection.document.return_value.set.assert_called_once()


def test_update_returns_none_when_document_missing(
    service: ItineraryService, mock_collection: MagicMock
) -> None:
    snapshot = MagicMock()
    snapshot.exists = False
    mock_collection.document.return_value.get.return_value = snapshot

    assert service.update("missing-id", {"name": "New Name"}) is None
