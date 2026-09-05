from __future__ import annotations

from pydantic import ValidationError

from app.exceptions import LLMGenerationError
from app.models.travel_ai import SuggestQuestionsRequest, SuggestQuestionsResponse
from app.services.ai import AIService
from app.services.prompts import questions_system_prompt


async def suggest_questions(
    ai: AIService, payload: SuggestQuestionsRequest
) -> SuggestQuestionsResponse:
    system_prompt = questions_system_prompt()
    prefs = payload.preferences.model_dump() if payload.preferences else None
    user_content = {"brief": payload.brief, "preferences": prefs}
    result = await ai.complete_json(system_prompt, user_content)
    try:
        return SuggestQuestionsResponse.model_validate(result)
    except ValidationError as exc:
        raise LLMGenerationError(
            "Model output did not match the expected questions shape", str(exc)
        ) from exc
