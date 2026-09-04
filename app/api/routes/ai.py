from fastapi import APIRouter, Depends

from app.deps.auth import CurrentUser, get_current_user
from app.deps.services import get_ai_service
from app.models.ai import ChatRequest, ChatResponse
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> ChatResponse:
    return await ai.chat(payload)
