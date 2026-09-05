"""Firebase Admin SDK initialization.

Single Responsibility: this module's only job is constructing a fully
initialized Firebase Admin App and the clients derived from it (Firestore,
Auth). It knows nothing about HTTP, routes, or business logic.

Dependency Inversion: routes and services should depend on the
`FirebaseClientFactory` protocol below (typically via the `get_firebase_admin`
FastAPI dependency), not on `firebase_admin` directly. That keeps every
consumer — deps/auth.py, deps/services.py, the service layer — trivially
mockable in tests without touching real Google credentials.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import firebase_admin
from firebase_admin import App, auth, credentials, firestore

from app.core.config import Settings, get_settings


class FirebaseClientFactory(Protocol):
    """Anything that can hand back a Firestore client and verify ID tokens.

    Depend on this Protocol (not on firebase_admin) in routes/services so
    a fake implementation can be swapped in under test.
    """

    def firestore_client(self) -> firestore.Client: ...

    def verify_id_token(self, id_token: str) -> dict[str, Any]: ...


class FirebaseAdmin:
    """Concrete FirebaseClientFactory backed by the real Firebase Admin SDK."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._app: App = self._init_app(settings)

    @staticmethod
    def _build_credentials(settings: Settings) -> credentials.Base:
        """Local dev: explicit service-account key file, if configured.
        Everywhere else (Cloud Run, CI): Application Default Credentials —
        Cloud Run injects the service identity automatically, no key file
        needed or wanted in the image.
        """
        key_path = settings.firebase_service_account_key_path
        if settings.environment != "production" and key_path:
            path = Path(key_path)
            if not path.is_file():
                raise FileNotFoundError(
                    f"firebase_service_account_key_path is set to {path!s}, "
                    "but no file exists there."
                )
            return credentials.Certificate(str(path))
        return credentials.ApplicationDefault()

    def _init_app(self, settings: Settings) -> App:
        # firebase_admin raises ValueError if you initialize_app() twice
        # under the same name — guard with get_app() so re-imports (tests,
        # dev autoreload) reuse the existing app instead of erroring.
        try:
            return firebase_admin.get_app(settings.firebase_app_name)
        except ValueError:
            cred = self._build_credentials(settings)
            options: dict[str, Any] | None = (
                {"projectId": settings.firebase_project_id}
                if settings.firebase_project_id
                else None
            )
            return firebase_admin.initialize_app(
                cred, options=options, name=settings.firebase_app_name
            )

    def firestore_client(self) -> firestore.Client:
        return firestore.client(self._app)

    def verify_id_token(self, id_token: str) -> dict[str, Any]:
        decoded: dict[str, Any] = auth.verify_id_token(id_token, app=self._app)
        return decoded


@lru_cache(maxsize=1)
def get_firebase_admin() -> FirebaseAdmin:
    """FastAPI dependency: one FirebaseAdmin (and one underlying Firebase
    App / connection pool) per process, built lazily on first use.
    """
    return FirebaseAdmin(get_settings())
