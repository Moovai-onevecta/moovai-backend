from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client as FirestoreClient

from app.core.config import get_settings


@lru_cache
def get_firebase_app() -> firebase_admin.App:
    settings = get_settings()
    if settings.google_application_credentials:
        cred = credentials.Certificate(settings.google_application_credentials)
    else:
        # Falls back to Application Default Credentials (e.g. on Cloud Run/GCE)
        cred = credentials.ApplicationDefault()
    return firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})


@lru_cache
def get_firestore_client() -> FirestoreClient:
    get_firebase_app()
    client: FirestoreClient = firestore.client()
    return client
