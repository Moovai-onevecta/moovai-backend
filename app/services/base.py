from __future__ import annotations

from abc import ABC
from typing import Any, Generic, Protocol, TypeVar

from google.cloud.firestore import Client, CollectionReference
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import BaseModel

from app.core.firestore_codec import decode_from_read, encode_for_write, snake_to_camel

ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)


class FirestoreProvider(Protocol):
    def firestore_client(
        self,
    ) -> Client: ...


class FirestoreService(
    Generic[ModelT],
    ABC,
):
    """Generic Firestore CRUD layer for a single collection.

    Field-naming (snake_case <-> camelCase) and None-handling are delegated
    entirely to app.core.firestore_codec, so every subclass — items,
    itineraries, users — gets consistent behavior for free rather than
    reimplementing it per collection.
    """

    collection_name: str

    # Name of the model field that holds the Firestore document ID, if any
    # (e.g. "id" for Itinerary). Leave as None for collections keyed by an
    # existing model field instead (e.g. UserProfile is keyed by `uid`,
    # which the caller already has — no generated ID needed).
    id_field: str | None = None

    def __init__(
        self,
        firestore_provider: FirestoreProvider,
    ) -> None:
        self._provider = firestore_provider

    @property
    def db(self) -> Client:
        return self._provider.firestore_client()

    @property
    def collection(self) -> CollectionReference:
        return self.db.collection(self.collection_name)

    def get_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        snapshot = self.collection.document(document_id).get()

        if not snapshot.exists:
            return None

        data = decode_from_read(snapshot.to_dict())

        # Firestore doesn't store the document ID as a field inside the
        # document itself — it's the path. Stitch it back onto the data
        # under id_field so model_validate() sees a complete record.
        if data is not None and self.id_field is not None:
            data[self.id_field] = snapshot.id

        return data

    def create_document(
        self,
        document_id: str,
        data: dict[str, Any],
    ) -> None:
        """Full-document write. Every field is written as given, including
        explicit Nones — this is a `.set()`, not a partial patch."""
        self.collection.document(document_id).set(encode_for_write(data))

    def update_document(
        self,
        document_id: str,
        data: dict[str, Any],
    ) -> None:
        """Partial write. Top-level None-valued keys are dropped so an
        unset field on the caller's side doesn't null out an existing
        value in Firestore — see encode_for_write's docstring."""
        self.collection.document(document_id).update(
            encode_for_write(data, exclude_none=True)
        )

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        self.collection.document(document_id).delete()

    def get_model(
        self,
        document_id: str,
        model_class: type[ModelT],
    ) -> ModelT | None:
        data = self.get_document(document_id)

        if data is None:
            return None

        return model_class.model_validate(data)

    def save_model(
        self,
        document_id: str,
        model: ModelT,
    ) -> None:
        self.create_document(
            document_id,
            model.model_dump(mode="json"),
        )

    def create_model(self, model: ModelT) -> ModelT:
        """Create a new document with a Firestore-generated ID, returning
        the model with that ID populated. Requires id_field to be set on
        the subclass — see the class-level docstring note above."""
        if self.id_field is None:
            raise NotImplementedError(
                f"{type(self).__name__} has no id_field configured; "
                "set id_field on the subclass to use create_model()."
            )

        doc_ref = self.collection.document()
        updated = model.model_copy(update={self.id_field: doc_ref.id})
        self.create_document(doc_ref.id, updated.model_dump(mode="json"))
        return updated

    def query_models(
        self,
        model_class: type[ModelT],
        *,
        field: str,
        equals: Any,
    ) -> list[ModelT]:
        """Equality-filter the collection on a snake_case model field name
        (translated to its stored camelCase key automatically, keeping the
        casing quirk in one place) and return validated models, with
        id_field populated from each document's ID.
        """
        firestore_field = snake_to_camel(field)
        results: list[ModelT] = []

        for snapshot in self.collection.where(
            filter=FieldFilter(firestore_field, "==", equals)
        ).stream():
            data = decode_from_read(snapshot.to_dict())

            if data is None:
                continue

            if self.id_field is not None:
                data[self.id_field] = snapshot.id

            results.append(model_class.model_validate(data))

        return results
