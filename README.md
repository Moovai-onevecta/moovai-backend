# MoovAI Backend

Python/FastAPI backend on Firebase (Firestore + Firebase Auth). AI features call a hosted
LLM API (Anthropic) over HTTPS — no models are hosted or run locally.

## Stack

- **FastAPI** — async web framework
- **Pydantic v2** — request/response validation and typed settings
- **mypy (strict)** — static type checking
- **firebase-admin** — Firestore access and Firebase ID token verification
- **httpx** — outbound calls to the AI provider's API

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in `.env`:
- `FIREBASE_PROJECT_ID` — your Firebase project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — path to a service account key JSON (local dev). In
  production (e.g. Cloud Run), omit this and Application Default Credentials are used instead.
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` — AI provider credentials

## Run

```bash
uvicorn app.main:app --reload
```

Docs at `http://localhost:8000/docs`.

## Auth

Endpoints that require a signed-in user expect `Authorization: Bearer <Firebase ID token>`.
The client (web/mobile app) signs in with Firebase Auth and sends the resulting ID token;
the backend verifies it via `firebase_admin.auth.verify_id_token`. The backend never handles
passwords directly.

## Type checking / linting / tests

```bash
mypy app
ruff check .
pytest
```
