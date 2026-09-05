from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import ProviderType

# TBD (requirements.md §5): exact lifecycle states and transitions.
ServiceRequestStatus = Literal[
    "pending", "offered", "accepted", "confirmed", "completed", "cancelled"
]


class ServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    itinerary_id: str
    destination_city: str = Field(min_length=1)
    service_type: ProviderType
    notes: str | None = None
    traveler_uid: str
    status: ServiceRequestStatus = "pending"
    provider_uid: str | None = None
    offered_price: float | None = None
