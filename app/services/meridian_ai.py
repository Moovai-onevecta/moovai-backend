from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.exceptions import LLMGenerationError


class MeridianAiService:
    """HTTP client for the meridian-ai microservice — the shared AI backend
    used across the Meridian product family. Structured generation (itinerary
    creation, clarifying questions) is delegated here instead of calling
    OpenAI directly, mirroring Meridian-Backend's MeridianAiService.php.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.meridian_ai_url.rstrip("/")
        self._token = settings.meridian_ai_service_token
        self._timeout = settings.meridian_ai_timeout

    async def generate_itinerary(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/generate_itinerary", payload)

    async def suggest_questions(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/suggest_questions", payload)

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/health")
                return response.status_code == httpx.codes.OK
        except httpx.HTTPError:
            return False

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}{path}", headers=headers, json=payload
                )
        except httpx.HTTPError as exc:
            raise LLMGenerationError(
                "Could not reach the meridian-ai service", str(exc)
            ) from exc

        if response.is_error:
            detail = response.text
            try:
                detail = response.json().get("error", {}).get("message", detail)
            except ValueError:
                pass
            raise LLMGenerationError(
                f"meridian-ai {path} failed [{response.status_code}]", detail
            )

        result: dict[str, Any] = response.json()
        return result
