from __future__ import annotations

from abc import ABC
from typing import Any, Generic, Protocol, TypeVar

from google.cloud.firestore import Client
from pydantic import BaseModel

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
    collection_name: str

    def __init__(
        self,
        firestore_provider: FirestoreProvider,
    ) -> None:
        self._provider = (
            firestore_provider
        )

    @property
    def db(self) -> Client:
        return self._provider.firestore_client()

    @property
    def collection(self):
        return self.db.collection(
            self.collection_name
        )

    def get_document(
        self,
        document_id: str,
    ) -> dict[str, Any] | None:
        snapshot = (
            self.collection.document(
                document_id
            ).get()
        )

        if not snapshot.exists:
            return None

        return snapshot.to_dict()

    def create_document(
        self,
        document_id: str,
        data: dict[str, Any],
    ) -> None:
        self.collection.document(
            document_id
        ).set(data)

    def update_document(
        self,
        document_id: str,
        data: dict[str, Any],
    ) -> None:
        self.collection.document(
            document_id
        ).update(data)

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        self.collection.document(
            document_id
        ).delete()

    def get_model(
        self,
        document_id: str,
        model_class: type[ModelT],
    ) -> ModelT | None:
        data = self.get_document(
            document_id
        )

        if data is None:
            return None

        return model_class.model_validate(
            data
        )

    def save_model(
        self,
        document_id: str,
        model: ModelT,
    ) -> None:
        self.create_document(
            document_id,
            model.model_dump(
                mode="json"
            ),
        )