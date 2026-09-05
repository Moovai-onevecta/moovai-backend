from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class UserRole(StrEnum):
    TRAVELER = "traveler"
    PROVIDER = "provider"


class ProviderType(StrEnum):
    TOUR_GUIDE = "tour_guide"
    TRANSPORT_PROVIDER = "transport_provider"


class UserProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    uid: str

    email: EmailStr | None = None

    display_name: str | None = None

    photo_url: str | None = None

    roles: set[UserRole] = Field(default_factory=lambda: {UserRole.TRAVELER})

    is_active: bool = True

    provider_type: ProviderType | None = None

    cities_served: list[str] = Field(default_factory=list)

    provider_bio: str | None = None

    created_at: datetime | None = None

    updated_at: datetime | None = None
