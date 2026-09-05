from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import get_service_requests_service
from app.models.service_request import ServiceRequest
from app.models.user import ProviderType
from app.services.service_requests import ServiceRequestsService

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


class ServiceRequestCreateRequest(BaseModel):
    """Excludes id/traveler_uid/status/provider_uid/offered_price — those are
    either server-assigned or come from the authenticated caller, never the
    client submitting the request.
    """

    model_config = ConfigDict(extra="forbid")

    itinerary_id: str
    destination_city: str
    service_type: ProviderType
    notes: str | None = None


@router.post("", response_model=ServiceRequest, status_code=status.HTTP_201_CREATED)
def create_service_request(
    payload: ServiceRequestCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    requests: ServiceRequestsService = Depends(get_service_requests_service),
) -> ServiceRequest:
    request = ServiceRequest(traveler_uid=user.uid, **payload.model_dump())
    return requests.create_model(request)


@router.get("/mine", response_model=list[ServiceRequest])
def list_my_requests(
    user: AuthenticatedUser = Depends(get_current_user),
    requests: ServiceRequestsService = Depends(get_service_requests_service),
) -> list[ServiceRequest]:
    return requests.list_for_traveler(user.uid)


@router.get("/for-city", response_model=list[ServiceRequest])
def list_requests_for_city(
    city: str,
    _user: AuthenticatedUser = Depends(get_current_user),
    requests: ServiceRequestsService = Depends(get_service_requests_service),
) -> list[ServiceRequest]:
    return requests.list_pending_for_city(city)


@router.post("/{request_id}/respond", response_model=ServiceRequest)
def respond_to_request(
    request_id: str,
    offered_price: float,
    user: AuthenticatedUser = Depends(get_current_user),
    requests: ServiceRequestsService = Depends(get_service_requests_service),
) -> ServiceRequest:
    updated = requests.respond(
        request_id, provider_uid=user.uid, offered_price=offered_price
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request not found"
        )
    return updated
