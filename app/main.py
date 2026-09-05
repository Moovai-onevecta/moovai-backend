from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    ai,
    bookings,
    health,
    itineraries,
    search,
    service_requests,
    users,
)
from app.core.config import get_settings
from app.exceptions import LLMGenerationError

settings = get_settings()

app = FastAPI(title="MoovAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LLMGenerationError)
def handle_llm_generation_error(
    _request: Request, exc: LLMGenerationError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "LLM_GENERATION_FAILED",
                "message": exc.message,
                "details": exc.detail,
            }
        },
    )


@app.exception_handler(ResponseValidationError)
def handle_response_validation_error(
    _request: Request, exc: ResponseValidationError
) -> JSONResponse:
    # The model's JSON parsed fine and passed our own model_validate (see the
    # *_ai service modules), but FastAPI's own response_model check still
    # failed. Kept as a distinct error code from LLM_GENERATION_FAILED so
    # callers can tell "the model said something odd" apart from "the
    # provider/network failed outright".
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "LLM_RESPONSE_INVALID",
                "message": "Model output did not match the expected shape",
                "details": str(exc),
            }
        },
    )


@app.exception_handler(Exception)
def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for anything not handled above (e.g. SerpApi/httpx errors
    raised by SearchService, which aren't wrapped in LLMGenerationError).

    Without this, Starlette's default handler returns a plain-text "Internal
    Server Error" body with no detail — the frontend's apiFetch expects JSON
    and would fail to even parse that response, let alone show a useful
    message. str(exc) is included here specifically so a failed call always
    surfaces whatever error message exists, not just the LLM-specific paths.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc) or exc.__class__.__name__,
                "details": None,
            }
        },
    )


app.include_router(health.router)
app.include_router(users.router)
app.include_router(itineraries.router)
app.include_router(service_requests.router)
app.include_router(bookings.router)
app.include_router(ai.router)
app.include_router(search.router)
