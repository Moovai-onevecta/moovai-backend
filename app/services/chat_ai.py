from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.itinerary import Itinerary
from app.models.travel_ai import ChatAssistantRequest, ChatAssistantResponse
from app.services.ai import AIService
from app.services.prompts import chat_assistant_system_prompt


async def chat_assistant(
    ai: AIService, payload: ChatAssistantRequest, itinerary: Itinerary
) -> ChatAssistantResponse:
    context = payload.context.model_dump() if payload.context else None
    # Exclude ownership/collaborator fields — irrelevant grounding for the
    # assistant and not something it should ever echo back or reason about.
    itinerary_snapshot = itinerary.model_dump(
        mode="json", exclude={"owner_uid", "collaborator_uids"}
    )
    system_prompt = chat_assistant_system_prompt(context, itinerary_snapshot)
    user_content = {"messages": [msg.model_dump() for msg in payload.messages]}
    result = await ai.complete_json(system_prompt, user_content)
    try:
        return ChatAssistantResponse.model_validate(result)
    except ValidationError as exc:
        raise LLMGenerationError(
            "Model output did not match the expected chat-assistant shape", str(exc)
        ) from exc
