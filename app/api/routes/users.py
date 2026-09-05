from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import get_users_service
from app.models.user import ProviderType, UserProfile, UserRole
from app.services.users import UsersService

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileUpsertRequest(BaseModel):
    """Excludes uid/is_active/created_at/updated_at — those are either
    server-assigned or come from the authenticated caller, never the client.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    display_name: str | None = None
    photo_url: str | None = None
    roles: set[UserRole] = Field(default_factory=lambda: {UserRole.TRAVELER})
    provider_type: ProviderType | None = None
    cities_served: list[str] = Field(default_factory=list)
    provider_bio: str | None = None


@router.put("/me", response_model=UserProfile)
def upsert_my_profile(
    payload: UserProfileUpsertRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    users: UsersService = Depends(get_users_service),
) -> UserProfile:
    profile = UserProfile(uid=user.uid, **payload.model_dump())
    return users.upsert_profile(profile)


@router.get("/me", response_model=UserProfile)
def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    users: UsersService = Depends(get_users_service),
) -> UserProfile:
    profile = users.get_profile(user.uid)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not set up yet"
        )
    return profile


@router.get("/providers", response_model=list[UserProfile])
def list_providers(
    city: str,
    _user: AuthenticatedUser = Depends(get_current_user),
    users: UsersService = Depends(get_users_service),
) -> list[UserProfile]:
    return users.list_providers_for_city(city)
