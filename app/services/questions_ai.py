from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.travel_ai import SuggestQuestionsRequest, SuggestQuestionsResponse
from app.services.meridian_ai import MeridianAiService
from app.services.meridian_mapping import build_questions_request


async def suggest_questions(
    ai: MeridianAiService, payload: SuggestQuestionsRequest
) -> SuggestQuestionsResponse:
    request = build_questions_request(payload)
    result = await ai.suggest_questions(request)
    try:
        return SuggestQuestionsResponse.model_validate(result)
    except ValidationError as exc:
        raise LLMGenerationError(
            "meridian-ai output did not match the expected questions shape", str(exc)
        ) from exc
