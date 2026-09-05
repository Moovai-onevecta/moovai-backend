"""Tests for the catch-all exception handler in app.main.

Anything not caught by a more specific handler (LLMGenerationError,
ResponseValidationError, FastAPI's own HTTPException/RequestValidationError)
should still come back as JSON with the real exception message — never
Starlette's default plain-text "Internal Server Error" body, which the
frontend's apiFetch can't even parse.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import handle_unexpected_error


def build_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(Exception, handle_unexpected_error)

    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise ValueError("SerpApi request failed: 401 Unauthorized")

    @router.get("/not-found")
    def not_found() -> None:
        raise HTTPException(status_code=404, detail="Item not found")

    app.include_router(router)
    return app


class TestUnexpectedErrorHandler:
    def test_returns_500_with_the_real_exception_message(self) -> None:
        client = TestClient(build_app(), raise_server_exceptions=False)

        response = client.get("/boom")

        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert body["error"]["message"] == "SerpApi request failed: 401 Unauthorized"

    def test_does_not_shadow_http_exception(self) -> None:
        client = TestClient(build_app(), raise_server_exceptions=False)

        response = client.get("/not-found")

        assert response.status_code == 404
        assert response.json() == {"detail": "Item not found"}
