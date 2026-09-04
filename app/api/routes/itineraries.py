"""Itinerary CRUD endpoints, owner-scoped.

Collaborator read/write access is intentionally NOT implemented here — the
permission model for collaborators is still an open question in
requirements.md (§4, §10.3). Every route below checks `owner_uid` only.
Revisit once that's decided (planned as build-plan step 15).

Request/response contract note: ItineraryCreateRequest/ItineraryUpdateRequest
deliberately exclude owner_uid/id/created_at/updated_at — those are either
server-assigned or come from the authenticated caller, never the client.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.core.deps.auth import AuthenticatedUser, get_current_user
from app.core.deps.services import get_itinerary_service
from app.models.itinerary import Destination, Flight, Itinerary
from app.services.itineraries import ItineraryService

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


class ItineraryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    start_date: date
    end_date: date
    destinations: list[Destination] = []
    flights: list[Flight] = []


class ItineraryUpdateRequest(BaseModel):
    """All fields optional — only the ones actually sent are applied.
    `exclude_unset=True` (see update_itinerary below) is what makes a PATCH
    a true partial update rather than resetting omitted fields to their
    defaults.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    destinations: list[Destination] | None = None
    flights: list[Flight] | None = None


def _get_owned_or_404(
    itinerary_id: str, user: AuthenticatedUser, service: ItineraryService
) -> Itinerary:
    itinerary = service.get_model(itinerary_id, Itinerary)

    # Same 404 for "doesn't exist" and "exists but isn't yours" — a 403
    # here would confirm to a non-owner that the itinerary exists at all.
    if itinerary is None or itinerary.owner_uid != user.uid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found"
        )

    return itinerary


@router.post("", response_model=Itinerary, status_code=status.HTTP_201_CREATED)
def create_itinerary(
    payload: ItineraryCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> Itinerary:
    itinerary = Itinerary(
        owner_uid=user.uid,
        name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        destinations=payload.destinations,
        flights=payload.flights,
    )
    return service.create(itinerary)


@router.get("", response_model=list[Itinerary])
def list_my_itineraries(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> list[Itinerary]:
    return service.list_for_owner(user.uid)


@router.get("/{itinerary_id}", response_model=Itinerary)
def get_itinerary(
    itinerary_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> Itinerary:
    return _get_owned_or_404(itinerary_id, user, service)


@router.patch("/{itinerary_id}", response_model=Itinerary)
def update_itinerary(
    itinerary_id: str,
    payload: ItineraryUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> Itinerary:
    _get_owned_or_404(itinerary_id, user, service)

    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)
    updated = service.update(itinerary_id, updates)

    # Existence + ownership were just confirmed above, so None here would
    # mean the document vanished between the check and the write.
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found"
        )

    return updated


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(
    itinerary_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ItineraryService = Depends(get_itinerary_service),
) -> None:
    _get_owned_or_404(itinerary_id, user, service)
    service.delete_document(itinerary_id)
