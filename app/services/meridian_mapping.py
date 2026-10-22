"""Translates between moovai's AI request/response models and meridian-ai's
wire format. The two services model itineraries differently (moovai: a flat
list of days with structured activities; meridian-ai: a dict of days keyed by
label, each holding a dict of destinations keyed by city) — this module is
the adapter so the rest of the codebase can keep using moovai's shapes.
"""

from __future__ import annotations

import re
from typing import Any

from app.models.travel_ai import (
    Cost,
    GenerateItineraryRequest,
    GenerateItineraryResponse,
    ItineraryActivity,
    ItineraryDay,
    ItineraryOption,
    SelectedFlight,
    SelectedStay,
    SuggestQuestionsRequest,
    TripPreferences,
)

_LEADING_INT = re.compile(r"\d+")


def _trip_spec(preferences: TripPreferences | None) -> dict[str, Any] | None:
    if preferences is None:
        return None
    return {
        "home_city": preferences.home_city,
        "start_date": preferences.start_date,
        "end_date": preferences.end_date,
        "budget": (
            {"amount": preferences.budget, "currency": preferences.currency}
            if preferences.budget is not None
            else None
        ),
        "travelers": {"count": preferences.traveler_count},
    }


def build_itinerary_request(payload: GenerateItineraryRequest) -> dict[str, Any]:
    preferences = payload.preferences
    return {
        "trip_brief": payload.brief,
        "trip_spec": _trip_spec(preferences),
        "preferences": preferences.model_dump() if preferences else None,
        "answered_questions": payload.answered_questions,
        "flight_candidates": payload.flight_candidates,
        "stay_candidates": payload.stay_candidates,
        "num_options": payload.num_options,
    }


def build_questions_request(payload: SuggestQuestionsRequest) -> dict[str, Any]:
    preferences = payload.preferences
    return {
        "trip_brief": payload.brief,
        "trip_spec": _trip_spec(preferences),
        "preferences": preferences.model_dump() if preferences else None,
    }


def _cost_from(
    amount: float | None, currency: str | None, is_estimate: bool
) -> Cost | None:
    if amount is None:
        return None
    return Cost(amount=amount, currency=currency or "USD", is_estimate=is_estimate)


def _day_number(label: str, fallback: int) -> int:
    match = _LEADING_INT.search(label)
    return int(match.group()) if match else fallback


def _parse_day(label: str, day: dict[str, Any], fallback_number: int) -> ItineraryDay:
    destinations: dict[str, Any] = day.get("destinations") or {}
    activities: list[ItineraryActivity] = []
    city: str | None = None
    for dest_name, dest in destinations.items():
        city = city or dest_name
        prefix = f"{dest_name}: " if len(destinations) > 1 else ""
        estimated_cost = dest.get("estimated_cost") or {}
        price = _cost_from(
            estimated_cost.get("amount"),
            estimated_cost.get("currency"),
            estimated_cost.get("is_estimate", True),
        )
        dest_activities = dest.get("activities") or []
        for i, title in enumerate(dest_activities):
            activities.append(
                ItineraryActivity(
                    title=f"{prefix}{title}",
                    price=price if i == 0 else None,
                )
            )

    return ItineraryDay(
        day_number=_day_number(label, fallback_number),
        city=city,
        date=None,
        activities=activities,
    )


def _parse_flight(flight: dict[str, Any]) -> SelectedFlight:
    return SelectedFlight(
        airline=flight.get("airline"),
        flight_number=flight.get("flight_number"),
        departure_airport=flight.get("departure_airport"),
        arrival_airport=flight.get("arrival_airport"),
        departure_time=flight.get("departure_datetime"),
        arrival_time=flight.get("arrival_datetime"),
        cost=_cost_from(
            flight.get("cost"), flight.get("currency"), flight.get("is_estimate", True)
        ),
        booking_url=flight.get("booking_url"),
    )


def _parse_stay(stay: dict[str, Any]) -> SelectedStay:
    return SelectedStay(
        name=stay["name"],
        address=stay.get("address"),
        check_in_date=stay.get("check_in_date"),
        check_out_date=stay.get("check_out_date"),
        cost_per_night=_cost_from(
            stay.get("cost_per_night"),
            stay.get("currency"),
            stay.get("is_estimate", True),
        ),
        booking_url=stay.get("booking_url"),
    )


def _parse_option(option: dict[str, Any]) -> ItineraryOption:
    days_raw: dict[str, Any] = option.get("days") or {}
    days = [
        _parse_day(label, day, fallback_number=i + 1)
        for i, (label, day) in enumerate(days_raw.items())
    ]
    total_cost_raw = option.get("total_cost") or {}
    return ItineraryOption(
        letter=option["letter"],
        name=option["name"],
        is_ai_pick=option.get("is_ai_pick", False),
        summary=option["summary"],
        total_cost=_cost_from(
            total_cost_raw.get("amount"),
            total_cost_raw.get("currency"),
            total_cost_raw.get("is_estimate", True),
        ),
        flights=[_parse_flight(f) for f in option.get("flights") or []],
        stays=[_parse_stay(s) for s in option.get("stays") or []],
        days=days,
    )


def parse_itinerary_response(data: dict[str, Any]) -> GenerateItineraryResponse:
    return GenerateItineraryResponse(
        options=[_parse_option(option) for option in data.get("options") or []]
    )
