from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai import ChatMessage

# ── shared ──


class Cost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: float | None = None
    currency: str = "USD"
    is_estimate: bool = True


class TripPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    home_city: str | None = None
    budget: float | None = None
    currency: str = "USD"
    traveler_count: int = 1
    start_date: str | None = None
    end_date: str | None = None
    dietary: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    max_stops: int | None = None
    travel_style: str | None = None


# ── destination suggestions ──


class SuggestDestinationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str
    preferences: TripPreferences | None = None
    num_suggestions: int = Field(default=3, ge=1, le=6)


class DestinationSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str
    country: str | None = None
    why: str
    best_months: list[str] = Field(default_factory=list)
    estimated_daily_budget: Cost | None = None


class SuggestDestinationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: list[DestinationSuggestion]


# ── clarifying questions ──


class SuggestQuestionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str
    preferences: TripPreferences | None = None


class SuggestedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    type: Literal["single_choice", "free_text"] = "single_choice"
    options: list[str] = Field(default_factory=list)


class SuggestQuestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[SuggestedQuestion]


# ── itinerary generation ──


class SelectedFlight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airline: str | None = None
    flight_number: str | None = None
    departure_airport: str | None = None
    arrival_airport: str | None = None
    departure_time: str | None = None
    arrival_time: str | None = None
    cost: Cost | None = None
    booking_url: str | None = None
    # Echoes flight_candidates[].id when the model picked a real search
    # result rather than estimating — lets the caller create a booking
    # record from the actual candidate instead of re-parsing LLM text.
    source_ref: str | None = None


class SelectedStay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    address: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    cost_per_night: Cost | None = None
    booking_url: str | None = None
    source_ref: str | None = None


class ItineraryActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    # Free-form duration label ("Est. 3 hrs", "Est. half day") — matches the
    # frontend itinerary page's existing badge copy directly.
    est: str | None = None
    price: Cost | None = None


class ItineraryDay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_number: int
    city: str | None = None
    date: str | None = None
    activities: list[ItineraryActivity] = Field(default_factory=list)


class ItineraryOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    letter: str
    name: str
    is_ai_pick: bool = False
    summary: str
    total_cost: Cost | None = None
    flights: list[SelectedFlight] = Field(default_factory=list)
    stays: list[SelectedStay] = Field(default_factory=list)
    days: list[ItineraryDay] = Field(default_factory=list)


class GenerateItineraryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str
    preferences: TripPreferences | None = None
    answered_questions: list[dict[str, str]] = Field(default_factory=list)
    # Optional real inventory — typically whatever SearchService.search_flights/
    # search_hotels just returned. When present the model is instructed to
    # build around these instead of inventing its own; absent, generation
    # still works with LLM-estimated pricing (Cost.is_estimate=True).
    flight_candidates: list[dict[str, object]] = Field(default_factory=list)
    stay_candidates: list[dict[str, object]] = Field(default_factory=list)
    num_options: int = Field(default=3, ge=1, le=3)


class GenerateItineraryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    options: list[ItineraryOption]


# ── chat assistant ──


class ChatContext(BaseModel):
    """Trip-shaped context the assistant grounds its reply in — mirrors what
    the frontend Chat page already tracks client-side (draft cities, brief).
    """

    model_config = ConfigDict(extra="forbid")

    brief: str | None = None
    preferences: TripPreferences | None = None
    cities: list[str] = Field(default_factory=list)


ActionKind = Literal["add_stop", "add_activity", "approve", "skip"]


class SuggestedAction(BaseModel):
    """Drives the approval/suggestion cards in the frontend Chat page (e.g.
    "Add Elmina as a stop") — the assistant proposes a concrete, addressable
    change rather than only prose.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: ActionKind
    title: str
    city: str | None = None
    blurb: str | None = None
    est: str | None = None
    price: Cost | None = None


class ChatAssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itinerary_id: str
    messages: list[ChatMessage] = Field(min_length=1)
    context: ChatContext | None = None


class ChatAssistantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reply: str
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
