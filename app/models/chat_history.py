"""Persisted chat + suggested-action history for an itinerary's planning
conversation. Distinct from app/models/travel_ai.py, which holds the
request/response DTOs for the AI call itself — these models are what
actually gets written to Firestore.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.travel_ai import ActionKind, Cost

Role = Literal["user", "assistant"]


class StoredChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role
    content: str
    created_at: datetime


class StoredChatAction(BaseModel):
    """A suggested_action the assistant proposed, plus how the traveler
    responded to it — the audit trail behind what was shown versus what
    actually got applied to the itinerary.
    """

    model_config = ConfigDict(extra="forbid")

    action_id: str
    kind: ActionKind
    title: str
    city: str | None = None
    blurb: str | None = None
    est: str | None = None
    price: Cost | None = None
    status: Literal["suggested", "approved", "skipped"] = "suggested"
    created_at: datetime
    resolved_at: datetime | None = None


class ChatHistory(BaseModel):
    """One document per itinerary — the full chat + suggested-action trail
    for that trip's planning conversation. Keyed by itinerary_id, not a
    generated id (see ChatHistoryService), mirroring UserProfile's
    uid-keyed pattern.
    """

    model_config = ConfigDict(extra="forbid")

    itinerary_id: str
    owner_uid: str
    messages: list[StoredChatMessage] = Field(default_factory=list)
    actions: list[StoredChatAction] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
