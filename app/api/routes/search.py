from fastapi import APIRouter, Depends

from app.deps.auth import AuthenticatedUser, get_current_user
from app.deps.services import get_search_service
from app.models.search import (
    DestinationSearchRequest,
    DestinationSearchResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    HotelSearchRequest,
    HotelSearchResponse,
)
from app.services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/flights", response_model=FlightSearchResponse)
async def search_flights(
    payload: FlightSearchRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    search: SearchService = Depends(get_search_service),
) -> FlightSearchResponse:
    results = await search.search_flights(
        departure_id=payload.departure_id,
        arrival_id=payload.arrival_id,
        outbound_date=payload.outbound_date,
        return_date=payload.return_date,
        adults=payload.adults,
    )
    return FlightSearchResponse(results=results)


@router.post("/hotels", response_model=HotelSearchResponse)
async def search_hotels(
    payload: HotelSearchRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    search: SearchService = Depends(get_search_service),
) -> HotelSearchResponse:
    results = await search.search_hotels(
        location=payload.location,
        check_in_date=payload.check_in_date,
        check_out_date=payload.check_out_date,
        adults=payload.adults,
    )
    return HotelSearchResponse(results=results)


@router.post("/destinations", response_model=DestinationSearchResponse)
async def search_destinations(
    payload: DestinationSearchRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
    search: SearchService = Depends(get_search_service),
) -> DestinationSearchResponse:
    results = await search.search_destinations(
        query=payload.query, num_results=payload.num_results
    )
    return DestinationSearchResponse(results=results)
