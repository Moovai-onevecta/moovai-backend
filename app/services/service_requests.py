from __future__ import annotations

from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firestore_codec import decode_from_read
from app.models.service_request import ServiceRequest
from app.services.base import FirestoreService


class ServiceRequestsService(FirestoreService[ServiceRequest]):
    """Firestore-backed CRUD for the provider-marketplace service requests."""

    collection_name = "service_requests"
    id_field = "id"

    def list_for_traveler(self, traveler_uid: str) -> list[ServiceRequest]:
        return self.query_models(
            ServiceRequest, field="traveler_uid", equals=traveler_uid
        )

    def list_pending_for_city(self, city: str) -> list[ServiceRequest]:
        # TBD (requirements.md §5): should only be visible to providers who
        # cover `city` — this returns all pending requests for the city;
        # scope it to the calling provider's coverage once the
        # targeted-vs-broadcast question is settled.
        query = self.collection.where(
            filter=FieldFilter("destinationCity", "==", city)
        ).where(filter=FieldFilter("status", "==", "pending"))

        results: list[ServiceRequest] = []
        for snapshot in query.stream():
            data = decode_from_read(snapshot.to_dict())
            if data is None:
                continue
            data["id"] = snapshot.id
            results.append(ServiceRequest.model_validate(data))
        return results

    def respond(
        self, request_id: str, provider_uid: str, offered_price: float
    ) -> ServiceRequest | None:
        existing = self.get_model(request_id, ServiceRequest)
        if existing is None:
            return None

        updated = existing.model_copy(
            update={
                "status": "offered",
                "provider_uid": provider_uid,
                "offered_price": offered_price,
            }
        )
        self.save_model(request_id, updated)
        return updated
