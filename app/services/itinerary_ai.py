from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.travel_ai import GenerateItineraryRequest, GenerateItineraryResponse
from app.services.ai import AIService
from app.services.prompts import itinerary_system_prompt


async def generate_itinerary(
    ai: AIService, payload: GenerateItineraryRequest
) -> GenerateItineraryResponse:
    system_prompt = itinerary_system_prompt(payload.num_options)
    prefs = payload.preferences.model_dump() if payload.preferences else None
    user_content = {
        "brief": payload.brief,
        "preferences": prefs,
        "answered_questions": payload.answered_questions,
        "flight_candidates": payload.flight_candidates,
        "stay_candidates": payload.stay_candidates,
    }
    result = await ai.complete_json(system_prompt, user_content)
    try:
        return GenerateItineraryResponse.model_validate(result)
    except ValidationError as exc:
        raise LLMGenerationError(
            "Model output did not match the expected itinerary shape", str(exc)
        ) from exc
