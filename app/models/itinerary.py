from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class Destination(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    order: int

    city: str

    country: str | None = None

    arrival_date: date

    departure_date: date


class Flight(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    carrier: str

    flight_number: str

    departure_airport: str

    arrival_airport: str

    departure_time: datetime

    arrival_time: datetime


class Itinerary(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    id: str | None = None

    name: str

    owner_uid: str

    collaborator_uids: list[str] = Field(default_factory=list)

    start_date: date

    end_date: date

    destinations: list[Destination] = Field(default_factory=list)

    flights: list[Flight] = Field(default_factory=list)

    created_at: datetime | None = None

    updated_at: datetime | None = None
