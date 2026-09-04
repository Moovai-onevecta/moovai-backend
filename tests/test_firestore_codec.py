"""Tests for app.core.firestore_codec.

Written first (TDD). Pure functions, no Firestore client involved — these
run instantly and need no mocking.
"""

from __future__ import annotations

import pytest

from app.core.firestore_codec import (
    camel_to_snake,
    decode_from_read,
    encode_for_write,
    keys_to_camel_case,
    keys_to_snake_case,
    snake_to_camel,
)


class TestKeyNameConversion:
    @pytest.mark.parametrize(
        ("snake", "camel"),
        [
            ("owner_uid", "ownerUid"),
            ("cities_served", "citiesServed"),
            ("created_at", "createdAt"),
            ("updated_at", "updatedAt"),
            ("provider_type", "providerType"),
            ("flight_number", "flightNumber"),
            ("uid", "uid"),
            ("id", "id"),
        ],
    )
    def test_snake_to_camel(self, snake: str, camel: str) -> None:
        assert snake_to_camel(snake) == camel

    @pytest.mark.parametrize(
        ("camel", "snake"),
        [
            ("ownerUid", "owner_uid"),
            ("citiesServed", "cities_served"),
            ("createdAt", "created_at"),
            ("updatedAt", "updated_at"),
            ("providerType", "provider_type"),
            ("flightNumber", "flight_number"),
            ("uid", "uid"),
            ("id", "id"),
        ],
    )
    def test_camel_to_snake(self, camel: str, snake: str) -> None:
        assert camel_to_snake(camel) == snake

    @pytest.mark.parametrize(
        "original",
        [
            "owner_uid",
            "cities_served",
            "start_date",
            "provider_bio",
            "flight_number",
            "uid",
        ],
    )
    def test_round_trip_snake_camel_snake(self, original: str) -> None:
        assert camel_to_snake(snake_to_camel(original)) == original


class TestKeysToCamelCase:
    def test_flat_dict(self) -> None:
        result = keys_to_camel_case({"owner_uid": "abc123", "start_date": "2026-06-01"})
        assert result == {"ownerUid": "abc123", "startDate": "2026-06-01"}

    def test_nested_dict_and_list(self) -> None:
        result = keys_to_camel_case(
            {
                "name": "Ghana Trip",
                "destinations": [
                    {"order": 1, "arrival_date": "2026-06-01"},
                    {"order": 2, "arrival_date": "2026-06-05"},
                ],
            }
        )
        assert result == {
            "name": "Ghana Trip",
            "destinations": [
                {"order": 1, "arrivalDate": "2026-06-01"},
                {"order": 2, "arrivalDate": "2026-06-05"},
            ],
        }

    def test_none_passes_through(self) -> None:
        assert keys_to_camel_case(None) is None

    def test_none_value_in_dict_is_preserved(self) -> None:
        result = keys_to_camel_case({"provider_type": None, "display_name": "Dave"})
        assert result == {"providerType": None, "displayName": "Dave"}

    def test_scalar_list_values_untouched(self) -> None:
        result = keys_to_camel_case({"collaborator_uids": ["a", "b", "c"]})
        assert result == {"collaboratorUids": ["a", "b", "c"]}


class TestKeysToSnakeCase:
    def test_flat_dict(self) -> None:
        result = keys_to_snake_case({"ownerUid": "abc123", "startDate": "2026-06-01"})
        assert result == {"owner_uid": "abc123", "start_date": "2026-06-01"}

    def test_nested_dict_and_list(self) -> None:
        result = keys_to_snake_case(
            {
                "name": "Ghana Trip",
                "destinations": [{"order": 1, "arrivalDate": "2026-06-01"}],
            }
        )
        assert result == {
            "name": "Ghana Trip",
            "destinations": [{"order": 1, "arrival_date": "2026-06-01"}],
        }

    def test_none_passes_through(self) -> None:
        assert keys_to_snake_case(None) is None

    def test_none_value_in_dict_is_preserved(self) -> None:
        assert keys_to_snake_case({"providerType": None}) == {"provider_type": None}


class TestEncodeForWrite:
    def test_default_keeps_none_values(self) -> None:
        result = encode_for_write({"provider_type": None, "display_name": "Dave"})
        assert result == {"providerType": None, "displayName": "Dave"}

    def test_exclude_none_drops_top_level_none_keys(self) -> None:
        result = encode_for_write(
            {"provider_type": None, "display_name": "Dave"}, exclude_none=True
        )
        assert result == {"displayName": "Dave"}
        assert "providerType" not in result

    def test_exclude_none_does_not_touch_nested_none(self) -> None:
        # Firestore .update() replaces nested maps wholesale, so partial-
        # update semantics only apply at the top level — we don't recurse.
        result = encode_for_write(
            {"destinations": [{"country": None, "city": "Accra"}]}, exclude_none=True
        )
        assert result == {"destinations": [{"country": None, "city": "Accra"}]}


class TestDecodeFromRead:
    def test_none_document_returns_none(self) -> None:
        assert decode_from_read(None) is None

    def test_converts_keys_back_to_snake_case(self) -> None:
        result = decode_from_read({"ownerUid": "abc123", "citiesServed": ["Accra"]})
        assert result == {"owner_uid": "abc123", "cities_served": ["Accra"]}

    def test_empty_dict_returns_empty_dict(self) -> None:
        assert decode_from_read({}) == {}


class TestRoundTrip:
    def test_encode_then_decode_preserves_data(self) -> None:
        original = {
            "owner_uid": "abc123",
            "cities_served": ["Accra", "Kumasi"],
            "provider_type": None,
        }

        written = encode_for_write(original)
        read_back = decode_from_read(written)

        assert read_back == original
