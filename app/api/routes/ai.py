from fastapi import APIRouter, Depends

from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import get_ai_service
from app.models.ai import ChatRequest, ChatResponse
from app.models.travel_ai import (
    ChatAssistantRequest,
    ChatAssistantResponse,
    GenerateItineraryRequest,
    GenerateItineraryResponse,
    SuggestDestinationsRequest,
    SuggestDestinationsResponse,
    SuggestQuestionsRequest,
    SuggestQuestionsResponse,
)
from app.services import chat_ai, destinations_ai, itinerary_ai, questions_ai
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> ChatResponse:
    return await ai.chat(payload)


@router.post("/chat/assistant", response_model=ChatAssistantResponse)
async def chat_assistant(
    payload: ChatAssistantRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> ChatAssistantResponse:
    """Structured chat reply for the itinerary-planning conversation — drives
    the suggestion/approval cards in the frontend Chat page, not just prose.
    """
    return await chat_ai.chat_assistant(ai, payload)


@router.post("/destinations/suggest", response_model=SuggestDestinationsResponse)
async def suggest_destinations(
    payload: SuggestDestinationsRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SuggestDestinationsResponse:
    return await destinations_ai.suggest_destinations(ai, payload)


@router.post("/questions/suggest", response_model=SuggestQuestionsResponse)
async def suggest_questions(
    payload: SuggestQuestionsRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SuggestQuestionsResponse:
    return await questions_ai.suggest_questions(ai, payload)


@router.post("/itineraries/generate", response_model=GenerateItineraryResponse)
async def generate_itinerary(
    payload: GenerateItineraryRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> GenerateItineraryResponse:
    return await itinerary_ai.generate_itinerary(ai, payload)
