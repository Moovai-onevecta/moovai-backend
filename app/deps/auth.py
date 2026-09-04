from __future__ import annotations

from dataclasses import Field
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole

from app.core.firebase import FirebaseClientFactory, get_firebase_admin


bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Normalized authenticated user extracted from Firebase."""

    model_config = ConfigDict(extra="allow")

    uid: str
    email: str | None = None
    roles: set[UserRole] = Field(default_factory=set)
    claims: dict[str, Any] = {}


def _extract_claims(decoded_token: dict[str, Any]) -> dict[str, Any]:
    """Remove standard Firebase/JWT fields and keep custom claims."""

    reserved = {
        "uid",
        "sub",
        "iss",
        "aud",
        "iat",
        "exp",
        "auth_time",
        "firebase",
        "email",
        "email_verified",
        "name",
        "picture",
    }

    return {key: value for key, value in decoded_token.items() if key not in reserved}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    firebase: FirebaseClientFactory = Depends(get_firebase_admin),
) -> AuthenticatedUser:
    """
    Verify Firebase ID token and return a typed user object.

    Raises:
        401 Unauthorized
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    try:
        decoded = firebase.verify_id_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from None

    uid = decoded.get("uid") or decoded.get("sub")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid",
        )

    roles = {UserRole(role) for role in decoded.get("roles", [])}

    return AuthenticatedUser(
        uid=uid,
        email=decoded.get("email"),
        roles=roles,
        claims=_extract_claims(decoded),
    )


def get_current_uid(
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    return user.uid


def require_role(role: UserRole):
    def dependency(
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:

        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return dependency


require_traveler = require_role(UserRole.TRAVELER)

require_provider = require_role(UserRole.PROVIDER)
