"""Tests for app.core.deps.auth.

Includes a regression test pinned to the `Field` import bug: importing
`dataclasses.Field` instead of `pydantic.Field` made `AuthenticatedUser`
crash the moment its class body was evaluated, so the whole module (and
anything importing it) would fail at import time.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps.auth import AuthenticatedUser, get_current_user
from app.models.user import UserRole


class TestAuthenticatedUserConstruction:
    def test_builds_with_defaults(self) -> None:
        # Regression: this line alone used to raise TypeError at import
        # time because of the dataclasses.Field bug.
        user = AuthenticatedUser(uid="abc123")

        assert user.roles == set()
        assert user.claims == {}

    def test_roles_defaults_are_independent_between_instances(self) -> None:
        first = AuthenticatedUser(uid="a")
        second = AuthenticatedUser(uid="b")

        first.roles.add(UserRole.TRAVELER)

        assert second.roles == set()


class TestGetCurrentUser:
    def test_raises_401_when_no_credentials(self) -> None:
        firebase = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=None, firebase=firebase)

        assert exc_info.value.status_code == 401

    def test_raises_401_when_token_verification_fails(self) -> None:
        firebase = MagicMock()
        firebase.verify_id_token.side_effect = ValueError("bad token")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=creds, firebase=firebase)

        assert exc_info.value.status_code == 401

    def test_returns_authenticated_user_from_decoded_token(self) -> None:
        firebase = MagicMock()
        firebase.verify_id_token.return_value = {
            "uid": "abc123",
            "email": "dave@example.com",
            "roles": ["traveler"],
            "iss": "https://example.com",
        }
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="good-token")

        user = get_current_user(credentials=creds, firebase=firebase)

        assert user.uid == "abc123"
        assert user.email == "dave@example.com"
        assert user.roles == {UserRole.TRAVELER}
        assert "iss" not in user.claims
