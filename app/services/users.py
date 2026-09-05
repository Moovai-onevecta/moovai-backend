from __future__ import annotations

from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.firestore_codec import decode_from_read
from app.models.user import UserProfile, UserRole
from app.services.base import FirestoreService


class UsersService(FirestoreService[UserProfile]):
    """Firestore-backed CRUD for user profiles, keyed by Firebase uid — not a
    generated document ID, so `id_field` is left unset (see
    FirestoreService.id_field docstring).
    """

    collection_name = "users"

    def get_profile(self, uid: str) -> UserProfile | None:
        return self.get_model(uid, UserProfile)

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        self.save_model(profile.uid, profile)
        return profile

    def list_providers_for_city(self, city: str) -> list[UserProfile]:
        # Firestore allows only one array_contains per query, so cities are
        # filtered server-side and the provider-role check happens in Python.
        query = self.collection.where(
            filter=FieldFilter("citiesServed", "array_contains", city)
        )

        results: list[UserProfile] = []
        for snapshot in query.stream():
            data = decode_from_read(snapshot.to_dict())
            if data is None:
                continue
            profile = UserProfile.model_validate(data)
            if UserRole.PROVIDER in profile.roles:
                results.append(profile)
        return results
