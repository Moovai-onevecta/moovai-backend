from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import (
    get_ai_service,
    get_chat_history_service,
    get_itinerary_service,
)
from app.models.ai import ChatRequest, ChatResponse
from app.models.chat_history import ChatHistory, StoredChatAction, StoredChatMessage
from app.models.itinerary import Itinerary
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
from app.services.chat_history import ChatHistoryService
from app.services.itineraries import ItineraryService

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_owned_itinerary_or_404(
    itinerary_id: str, user: AuthenticatedUser, itineraries: ItineraryService
) -> Itinerary:
    itinerary = itineraries.get_model(itinerary_id, Itinerary)

    # Same 404 for "doesn't exist" and "exists but isn't yours" — a 403 here
    # would confirm to a non-owner that the itinerary exists at all.
    if itinerary is None or itinerary.owner_uid != user.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found"
        )

    return itinerary


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
    user: AuthenticatedUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
    itineraries: ItineraryService = Depends(get_itinerary_service),
    chat_history: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatAssistantResponse:
    """Structured chat reply for the itinerary-planning conversation — drives
    the suggestion/approval cards in the frontend Chat page, not just prose.

    Also persists the exchange (latest user message, assistant reply, and
    any suggested actions) to that itinerary's chat history in Firestore.
    """
    itinerary = _get_owned_itinerary_or_404(payload.itinerary_id, user, itineraries)

    response = await chat_ai.chat_assistant(ai, payload, itinerary)

    now = datetime.now(UTC)
    latest_user_message = payload.messages[-1]
    chat_history.append_messages(
        payload.itinerary_id,
        user.uid,
        [
            StoredChatMessage(
                role=latest_user_message.role,
                content=latest_user_message.content,
                created_at=now,
            ),
            StoredChatMessage(role="assistant", content=response.reply, created_at=now),
        ],
    )

    if response.suggested_actions:
        chat_history.append_actions(
            payload.itinerary_id,
            user.uid,
            [
                StoredChatAction(
                    action_id=action.id,
                    kind=action.kind,
                    title=action.title,
                    city=action.city,
                    blurb=action.blurb,
                    est=action.est,
                    price=action.price,
                    created_at=now,
                )
                for action in response.suggested_actions
            ],
        )

    return response


@router.get("/chat/{itinerary_id}/history", response_model=ChatHistory)
def get_chat_history(
    itinerary_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    itineraries: ItineraryService = Depends(get_itinerary_service),
    chat_history: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistory:
    _get_owned_itinerary_or_404(itinerary_id, user, itineraries)

    history = chat_history.get_for_itinerary(itinerary_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No chat history yet"
        )

    return history


class ResolveActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool


@router.post(
    "/chat/{itinerary_id}/actions/{action_id}/resolve", response_model=ChatHistory
)
def resolve_chat_action(
    itinerary_id: str,
    action_id: str,
    payload: ResolveActionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    itineraries: ItineraryService = Depends(get_itinerary_service),
    chat_history: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatHistory:
    """Records whether the traveler approved or skipped a previously
    suggested action — the frontend calls this from respondToAction.
    """
    _get_owned_itinerary_or_404(itinerary_id, user, itineraries)

    updated = chat_history.resolve_action(itinerary_id, action_id, payload.accepted)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat history not found"
        )

    return updated


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
