"""Tests for app.services.base.FirestoreService.

Focus of this file: proving every read/write path runs through
app.core.firestore_codec, so camelCase translation and None-safe handling
apply uniformly to every collection (items, itineraries, users) without
each subclass having to remember to do it itself. Also covers id_field
injection and generic equality querying, added for services (itineraries)
that expose a Firestore-generated document ID and need to filter by owner.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from app.services.base import FirestoreService


class _DummyModel(BaseModel):
    id: str | None = None
    owner_uid: str
    provider_type: str | None = None


class _DummyService(FirestoreService[_DummyModel]):
    collection_name = "dummy_collection"


class _DummyServiceWithId(FirestoreService[_DummyModel]):
    collection_name = "dummy_with_id"
    id_field = "id"


@pytest.fixture
def mock_collection() -> MagicMock:
    return MagicMock(name="collection")


@pytest.fixture
def service(mock_collection: MagicMock) -> _DummyService:
    provider = MagicMock()
    db = MagicMock()
    db.collection.return_value = mock_collection
    provider.firestore_client.return_value = db
    return _DummyService(provider)


@pytest.fixture
def service_with_id(mock_collection: MagicMock) -> _DummyServiceWithId:
    provider = MagicMock()
    db = MagicMock()
    db.collection.return_value = mock_collection
    provider.firestore_client.return_value = db
    return _DummyServiceWithId(provider)


class TestGetDocument:
    def test_returns_none_when_document_does_not_exist(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = False
        mock_collection.document.return_value.get.return_value = snapshot

        assert service.get_document("missing-id") is None

    def test_decodes_camel_case_keys_from_snapshot(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.to_dict.return_value = {"ownerUid": "abc123", "providerType": None}
        mock_collection.document.return_value.get.return_value = snapshot

        result = service.get_document("doc-1")

        assert result == {"owner_uid": "abc123", "provider_type": None}


class TestCreateDocument:
    def test_encodes_to_camel_case_and_keeps_none(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        service.create_document("doc-1", {"owner_uid": "abc123", "provider_type": None})

        mock_collection.document.return_value.set.assert_called_once_with(
            {"ownerUid": "abc123", "providerType": None}
        )


class TestUpdateDocument:
    def test_encodes_to_camel_case_and_drops_top_level_none(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        service.update_document("doc-1", {"owner_uid": "abc123", "provider_type": None})

        mock_collection.document.return_value.update.assert_called_once_with(
            {"ownerUid": "abc123"}
        )


class TestDeleteDocument:
    def test_delegates_to_document_delete(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        service.delete_document("doc-1")

        mock_collection.document.return_value.delete.assert_called_once()


class TestGetModel:
    def test_validates_decoded_data_into_model(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.to_dict.return_value = {"ownerUid": "abc123"}
        mock_collection.document.return_value.get.return_value = snapshot

        model = service.get_model("doc-1", _DummyModel)

        assert model == _DummyModel(owner_uid="abc123")

    def test_returns_none_when_document_missing(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = False
        mock_collection.document.return_value.get.return_value = snapshot

        assert service.get_model("doc-1", _DummyModel) is None


class TestSaveModel:
    def test_encodes_model_dump_to_camel_case(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        model = _DummyModel(owner_uid="abc123", provider_type=None)

        service.save_model("doc-1", model)

        mock_collection.document.return_value.set.assert_called_once_with(
            {"id": None, "ownerUid": "abc123", "providerType": None}
        )


class TestIdFieldInjection:
    def test_get_document_leaves_data_untouched_when_id_field_not_set(
        self, service: _DummyService, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.id = "doc-1"
        snapshot.to_dict.return_value = {"ownerUid": "abc123"}
        mock_collection.document.return_value.get.return_value = snapshot

        result = service.get_document("doc-1")

        assert result == {"owner_uid": "abc123"}

    def test_get_document_injects_snapshot_id_when_id_field_set(
        self, service_with_id: _DummyServiceWithId, mock_collection: MagicMock
    ) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.id = "doc-1"
        snapshot.to_dict.return_value = {"ownerUid": "abc123"}
        mock_collection.document.return_value.get.return_value = snapshot

        result = service_with_id.get_document("doc-1")

        assert result == {"id": "doc-1", "owner_uid": "abc123"}


class TestCreateModel:
    def test_generates_id_and_saves_model(
        self, service_with_id: _DummyServiceWithId, mock_collection: MagicMock
    ) -> None:
        doc_ref = MagicMock()
        doc_ref.id = "generated-id-1"
        mock_collection.document.return_value = doc_ref
        model = _DummyModel(owner_uid="abc123")

        result = service_with_id.create_model(model)

        assert result.id == "generated-id-1"
        doc_ref.set.assert_called_once_with(
            {"id": "generated-id-1", "ownerUid": "abc123", "providerType": None}
        )

    def test_raises_when_id_field_not_configured(self, service: _DummyService) -> None:
        with pytest.raises(NotImplementedError):
            service.create_model(_DummyModel(owner_uid="abc123"))


class TestQueryModels:
    def test_filters_by_camel_case_field_and_returns_validated_models(
        self, service_with_id: _DummyServiceWithId, mock_collection: MagicMock
    ) -> None:
        snap1 = MagicMock()
        snap1.id = "id-1"
        snap1.to_dict.return_value = {"ownerUid": "abc123"}
        snap2 = MagicMock()
        snap2.id = "id-2"
        snap2.to_dict.return_value = {"ownerUid": "abc123"}
        mock_collection.where.return_value.stream.return_value = [snap1, snap2]

        results = service_with_id.query_models(
            _DummyModel, field="owner_uid", equals="abc123"
        )

        # FieldFilter has no value-based __eq__ in the installed
        # google-cloud-firestore version, so two separately constructed
        # instances are never `==` even when semantically identical —
        # compare the fields the query actually depends on instead.
        mock_collection.where.assert_called_once()
        called_filter = mock_collection.where.call_args.kwargs["filter"]
        actual = (
            called_filter.field_path,
            called_filter.op_string,
            called_filter.value,
        )
        assert actual == ("ownerUid", "==", "abc123")
        assert results == [
            _DummyModel(id="id-1", owner_uid="abc123"),
            _DummyModel(id="id-2", owner_uid="abc123"),
        ]
