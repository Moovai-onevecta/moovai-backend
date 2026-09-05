from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ── flights (SerpApi google_flights engine) ──


class FlightSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    departure_id: str  # IATA airport/city code, e.g. "ACC"
    arrival_id: str
    outbound_date: str  # "YYYY-MM-DD"
    return_date: str | None = None
    adults: int = Field(default=1, ge=1)


class FlightLeg(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airline: str | None = None
    flight_number: str | None = None
    departure_airport: str | None = None
    departure_time: str | None = None
    arrival_airport: str | None = None
    arrival_time: str | None = None
    duration_minutes: int | None = None


class FlightResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    price: float | None = None
    currency: str = "USD"
    total_duration_minutes: int | None = None
    stops: int = 0
    airline_logo: str | None = None
    legs: list[FlightLeg] = Field(default_factory=list)
    booking_token: str | None = None


class FlightSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[FlightResult]


# ── hotels/stays (SerpApi google_hotels engine) ──


class HotelSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str
    check_in_date: str
    check_out_date: str
    adults: int = Field(default=1, ge=1)


class HotelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_token: str | None = None
    name: str
    link: str | None = None
    hotel_class: str | None = None
    overall_rating: float | None = None
    rate_per_night: float | None = None
    total_rate: float | None = None
    currency: str = "USD"
    thumbnail: str | None = None


class HotelSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[HotelResult]


# ── destinations (SerpApi google engine, general search) ──


class DestinationSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    num_results: int = Field(default=5, ge=1, le=10)


class DestinationSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    snippet: str | None = None
    link: str | None = None
    thumbnail: str | None = None


class DestinationSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[DestinationSearchResult]
