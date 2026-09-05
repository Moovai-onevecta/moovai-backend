from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.travel_ai import SuggestDestinationsRequest, SuggestDestinationsResponse
from app.services.ai import AIService
from app.services.prompts import destinations_system_prompt


async def suggest_destinations(
    ai: AIService, payload: SuggestDestinationsRequest
) -> SuggestDestinationsResponse:
    system_prompt = destinations_system_prompt(payload.num_suggestions)
    prefs = payload.preferences.model_dump() if payload.preferences else None
    user_content = {"brief": payload.brief, "preferences": prefs}
    result = await ai.complete_json(system_prompt, user_content)
    try:
        return SuggestDestinationsResponse.model_validate(result)
    except ValidationError as exc:
        raise LLMGenerationError(
            "Model output did not match the expected destination-suggestion shape",
            str(exc),
        ) from exc
