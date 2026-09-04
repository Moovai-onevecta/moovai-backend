from datetime import date, datetime

import pytest

from app.models.itinerary import (
    Destination,
    Flight,
    Itinerary,
)


def test_create_itinerary():
    itinerary = Itinerary(
        name="Portugal Trip",
        owner_uid="user123",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 10),
    )

    assert itinerary.name == "Portugal Trip"
    assert itinerary.owner_uid == "user123"


def test_destination_order():
    destination = Destination(
        order=1,
        city="Lisbon",
        arrival_date=date(2026, 5, 1),
        departure_date=date(2026, 5, 5),
    )

    assert destination.order == 1


def test_destination_departure_after_arrival():
    with pytest.raises(ValueError):
        Destination(
            order=1,
            city="Lisbon",
            arrival_date=date(2026, 5, 5),
            departure_date=date(2026, 5, 1),
        )


def test_flight_arrival_after_departure():
    with pytest.raises(ValueError):
        Flight(
            carrier="TAP",
            flight_number="TP123",
            departure_airport="JFK",
            arrival_airport="LIS",
            departure_time=datetime(2026, 5, 1, 12, 0),
            arrival_time=datetime(2026, 5, 1, 10, 0),
        )


def test_itinerary_end_after_start():
    with pytest.raises(ValueError):
        Itinerary(
            name="Portugal",
            owner_uid="123",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 5, 1),
        )
