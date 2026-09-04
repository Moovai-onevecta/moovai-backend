from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.firebase import get_firestore_client
from app.services.ai import AIService
from app.services.items import ItemsService


def get_items_service() -> ItemsService:
    return ItemsService(get_firestore_client())


def get_ai_service(settings: Settings = Depends(get_settings)) -> AIService:
    return AIService(settings)
