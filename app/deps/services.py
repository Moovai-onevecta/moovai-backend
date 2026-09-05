from __future__ import annotations

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.firebase import FirebaseClientFactory, get_firebase_admin
from app.services.ai import AIService
from app.services.chat_history import ChatHistoryService
from app.services.itineraries import ItineraryService
from app.services.search import SearchService
from app.services.service_requests import ServiceRequestsService
from app.services.users import UsersService


def get_firestore_provider() -> FirebaseClientFactory:
    return get_firebase_admin()


def get_itinerary_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> ItineraryService:
    return ItineraryService(provider)


def get_users_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> UsersService:
    return UsersService(provider)


def get_service_requests_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> ServiceRequestsService:
    return ServiceRequestsService(provider)


def get_chat_history_service(
    provider: FirebaseClientFactory = Depends(get_firestore_provider),
) -> ChatHistoryService:
    return ChatHistoryService(provider)


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
    return AIService(settings)


def get_search_service(settings: Settings = Depends(get_settings)) -> SearchService:
    return SearchService(settings)
