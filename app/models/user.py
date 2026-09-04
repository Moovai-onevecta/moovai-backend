from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    TRAVELER = "traveler"
    PROVIDER = "provider"


class ProviderType(StrEnum):
    TOUR_GUIDE = "tour_guide"
    TRANSPORT_PROVIDER = "transport_provider"


class UserProfile(BaseModel):
    """
    Firestore document stored in users/{uid}
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    uid: str
    email: str | None = None
    display_name: str | None = None
    roles: set[UserRole] = Field(default_factory=lambda: {UserRole.TRAVELER})
    provider_type: ProviderType | None = None
    cities_served: list[str] = Field(default_factory=list)
    is_active: bool = True
