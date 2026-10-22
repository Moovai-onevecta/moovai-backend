from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.travel_ai import GenerateItineraryRequest, GenerateItineraryResponse
from app.services.meridian_ai import MeridianAiService
from app.services.meridian_mapping import (
    build_itinerary_request,
    parse_itinerary_response,
)


async def generate_itinerary(
    ai: MeridianAiService, payload: GenerateItineraryRequest
) -> GenerateItineraryResponse:
    request = build_itinerary_request(payload)
    result = await ai.generate_itinerary(request)
    try:
        return parse_itinerary_response(result)
    except (ValidationError, KeyError) as exc:
        raise LLMGenerationError(
            "meridian-ai output did not match the expected itinerary shape", str(exc)
        ) from exc
