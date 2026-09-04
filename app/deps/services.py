from __future__ import annotations

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.firebase import FirebaseClientFactory, get_firebase_admin
from app.services.ai import AIService
from app.services.items import ItemsService
from app.services.itineraries import ItineraryService


def get_firestore_provider() -> FirebaseClientFactory:
    return get_firebase_admin()


def get_items_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> ItemsService:
    return ItemsService(provider)


def get_itinerary_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> ItineraryService:
    return ItineraryService(provider)


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
    return AIService(settings)
