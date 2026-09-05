"""SerpApi-backed flight, hotel, and destination search.

Unlike the AI service, results here are real inventory/search results, not
LLM output — this module owns the one external non-LLM API call the travel
features need. `app/services/itinerary_ai.py` passes whatever this returns
straight through to the AI service as `flight_candidates`/`stay_candidates`.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.models.search import (
    DestinationSearchResult,
    FlightLeg,
    FlightResult,
    HotelResult,
)

_SERPAPI_URL = "https://serpapi.com/search.json"


class SearchService:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.serpapi_api_key

    async def search_flights(
        self,
        *,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        return_date: str | None = None,
        adults: int = 1,
    ) -> list[FlightResult]:
        params: dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "adults": adults,
            "type": "1" if return_date is None else "2",  # 1=one-way, 2=round-trip
            "api_key": self._api_key,
        }
        if return_date is not None:
            params["return_date"] = return_date

        data = await self._get(params)
        raw_flights = [*data.get("best_flights", []), *data.get("other_flights", [])]
        return [self._parse_flight(i, item) for i, item in enumerate(raw_flights)]

    async def search_hotels(
        self,
        *,
        location: str,
        check_in_date: str,
        check_out_date: str,
        adults: int = 1,
    ) -> list[HotelResult]:
        params = {
            "engine": "google_hotels",
            "q": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "api_key": self._api_key,
        }
        data = await self._get(params)
        return [self._parse_hotel(item) for item in data.get("properties", [])]

    async def search_destinations(
        self, *, query: str, num_results: int = 5
    ) -> list[DestinationSearchResult]:
        params = {
            "engine": "google",
            "q": f"{query} travel guide",
            "num": num_results,
            "api_key": self._api_key,
        }
        data = await self._get(params)
        results = data.get("organic_results", [])[:num_results]
        return [
            DestinationSearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet"),
                link=item.get("link"),
                thumbnail=item.get("thumbnail"),
            )
            for item in results
        ]

    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(_SERPAPI_URL, params=params)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

    @staticmethod
    def _parse_flight(index: int, item: dict[str, Any]) -> FlightResult:
        legs = [
            FlightLeg(
                airline=leg.get("airline"),
                flight_number=leg.get("flight_number"),
                departure_airport=(leg.get("departure_airport") or {}).get("id"),
                departure_time=(leg.get("departure_airport") or {}).get("time"),
                arrival_airport=(leg.get("arrival_airport") or {}).get("id"),
                arrival_time=(leg.get("arrival_airport") or {}).get("time"),
                duration_minutes=leg.get("duration"),
            )
            for leg in item.get("flights", [])
        ]
        return FlightResult(
            id=item.get("booking_token") or f"flt_{index}",
            price=item.get("price"),
            total_duration_minutes=item.get("total_duration"),
            stops=max(len(legs) - 1, 0),
            airline_logo=(
                item.get("airline_logo") or (legs[0].airline if legs else None)
            ),
            legs=legs,
            booking_token=item.get("booking_token"),
        )

    @staticmethod
    def _parse_hotel(item: dict[str, Any]) -> HotelResult:
        rate_per_night = item.get("rate_per_night") or {}
        total_rate = item.get("total_rate") or {}
        images = item.get("images") or []
        return HotelResult(
            property_token=item.get("property_token"),
            name=item.get("name", ""),
            link=item.get("link"),
            hotel_class=item.get("hotel_class"),
            overall_rating=item.get("overall_rating"),
            rate_per_night=rate_per_night.get("extracted_lowest"),
            total_rate=total_rate.get("extracted_lowest"),
            thumbnail=images[0].get("thumbnail") if images else None,
        )
