from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.itinerary import Itinerary
from app.services.base import FirestoreService


class ItineraryService(FirestoreService[Itinerary]):
    """Firestore-backed CRUD for itineraries.

    Deliberately minimal: raw create/read/update/delete and ID handling
    all come from FirestoreService. This class only adds what itineraries
    specifically need on top: filtering by owner, and timestamping.
    """

    collection_name = "itineraries"
    id_field = "id"

    def list_for_owner(self, owner_uid: str) -> list[Itinerary]:
        return self.query_models(Itinerary, field="owner_uid", equals=owner_uid)

    def create(self, itinerary: Itinerary) -> Itinerary:
        now = datetime.now(UTC)
        stamped = itinerary.model_copy(update={"created_at": now, "updated_at": now})
        return self.create_model(stamped)

    def update(self, itinerary_id: str, updates: dict[str, Any]) -> Itinerary | None:
        """Merge `updates` onto the existing document and re-validate the
        whole model (not model_copy) so cross-field rules — e.g. Itinerary's
        end_date >= start_date check — run against the merged result, not
        just the fields that changed.
        """
        existing = self.get_model(itinerary_id, Itinerary)

        if existing is None:
            return None

        merged = existing.model_dump()
        merged.update(updates)
        merged["updated_at"] = datetime.now(UTC)

        updated = Itinerary.model_validate(merged)
        self.save_model(itinerary_id, updated)
        return updated
