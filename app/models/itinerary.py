from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Destination(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    order: int
    city: str
    country: str | None = None
    arrival_date: date
    departure_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> Destination:
        if self.departure_date < self.arrival_date:
            raise ValueError("departure_date must be on or after arrival_date")

        return self


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

    @model_validator(mode="after")
    def validate_times(self) -> Flight:
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time must be after departure_time")

        return self


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

    @model_validator(mode="after")
    def validate_dates(self) -> Itinerary:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")

        return self

    @model_validator(mode="after")
    def validate_destination_order(self) -> Itinerary:
        orders = [destination.order for destination in self.destinations]

        if len(orders) != len(set(orders)):
            raise ValueError("destination order values must be unique")

        return self
