from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

from app.core.firebase import get_firebase_app

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None
    claims: dict[str, object]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    get_firebase_app()
    try:
        decoded = firebase_auth.verify_id_token(credentials.credentials)
    except Exception as exc:  # firebase_admin raises several distinct exception types
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    return CurrentUser(
        uid=decoded["uid"],
        email=decoded.get("email"),
        claims=decoded,
    )
