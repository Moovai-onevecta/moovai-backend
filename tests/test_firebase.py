"""Tests for app.core.firebase.

Written first (TDD): these define the contract for FirebaseAdmin before
any implementation exists. All Google/Firebase calls are mocked — no
network access and no real credentials are needed to run this suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.core.firebase import FirebaseAdmin, get_firebase_admin


def make_settings(**overrides: object) -> Settings:
    """Build a Settings instance with sane test defaults, overridable per test."""
    defaults: dict[str, object] = {
        "environment": "production",
        "firebase_project_id": "moovai-test",
        "firebase_service_account_key_path": None,
        "firebase_app_name": "moovai-test-app",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _clear_firebase_admin_cache() -> None:
    """get_firebase_admin() is lru_cache'd; each test should see a clean slate."""
    get_firebase_admin.cache_clear()


@pytest.fixture
def mock_firebase_admin(mocker: pytest_mock.MockerFixture) -> MagicMock:  # noqa: F821
    """Patch the firebase_admin module functions that FirebaseAdmin calls."""
    module = mocker.patch("app.core.firebase.firebase_admin")
    module.get_app.side_effect = ValueError("no app with this name exists")
    module.initialize_app.return_value = MagicMock(name="fake_app")
    return module


@pytest.fixture
def mock_credentials(mocker: pytest_mock.MockerFixture) -> MagicMock:  # noqa: F821
    return mocker.patch("app.core.firebase.credentials")


@pytest.fixture
def mock_auth(mocker: pytest_mock.MockerFixture) -> MagicMock:  # noqa: F821
    return mocker.patch("app.core.firebase.auth")


@pytest.fixture
def mock_firestore(mocker: pytest_mock.MockerFixture) -> MagicMock:  # noqa: F821
    return mocker.patch("app.core.firebase.firestore")


class TestCredentialSelection:
    def test_production_uses_application_default_credentials(
        self, mock_firebase_admin: MagicMock, mock_credentials: MagicMock
    ) -> None:
        settings = make_settings(
            environment="production", firebase_service_account_key_path=None
        )

        FirebaseAdmin(settings)

        mock_credentials.ApplicationDefault.assert_called_once()
        mock_credentials.Certificate.assert_not_called()

    def test_local_with_key_path_uses_certificate_credentials(
        self,
        tmp_path: Path,
        mock_firebase_admin: MagicMock,
        mock_credentials: MagicMock,
    ) -> None:
        key_file = tmp_path / "service-account.json"
        key_file.write_text("{}")
        settings = make_settings(
            environment="local", firebase_service_account_key_path=str(key_file)
        )

        FirebaseAdmin(settings)

        mock_credentials.Certificate.assert_called_once_with(str(key_file))
        mock_credentials.ApplicationDefault.assert_not_called()

    def test_local_without_key_path_falls_back_to_application_default(
        self, mock_firebase_admin: MagicMock, mock_credentials: MagicMock
    ) -> None:
        settings = make_settings(
            environment="local", firebase_service_account_key_path=None
        )

        FirebaseAdmin(settings)

        mock_credentials.ApplicationDefault.assert_called_once()

    def test_local_with_missing_key_file_raises(
        self, mock_firebase_admin: MagicMock, mock_credentials: MagicMock
    ) -> None:
        settings = make_settings(
            environment="local",
            firebase_service_account_key_path="/nonexistent/service-account.json",
        )

        with pytest.raises(FileNotFoundError):
            FirebaseAdmin(settings)


class TestAppInitialization:
    def test_initializes_app_once_with_configured_name_and_project(
        self, mock_firebase_admin: MagicMock, mock_credentials: MagicMock
    ) -> None:
        settings = make_settings(
            firebase_app_name="my-app", firebase_project_id="my-project"
        )

        FirebaseAdmin(settings)

        mock_firebase_admin.initialize_app.assert_called_once()
        _, kwargs = mock_firebase_admin.initialize_app.call_args
        assert kwargs["name"] == "my-app"
        assert kwargs["options"] == {"projectId": "my-project"}

    def test_reuses_existing_app_instead_of_reinitializing(
        self, mock_firebase_admin: MagicMock, mock_credentials: MagicMock
    ) -> None:
        existing_app = MagicMock(name="already_initialized_app")
        mock_firebase_admin.get_app.side_effect = None
        mock_firebase_admin.get_app.return_value = existing_app
        settings = make_settings()

        admin = FirebaseAdmin(settings)

        mock_firebase_admin.initialize_app.assert_not_called()
        assert admin._app is existing_app


class TestFirestoreClient:
    def test_firestore_client_delegates_to_firestore_module_with_app(
        self,
        mock_firebase_admin: MagicMock,
        mock_credentials: MagicMock,
        mock_firestore: MagicMock,
    ) -> None:
        settings = make_settings()
        admin = FirebaseAdmin(settings)
        mock_firestore.client.return_value = "fake-firestore-client"

        client = admin.firestore_client()

        mock_firestore.client.assert_called_once_with(admin._app)
        assert client == "fake-firestore-client"


class TestVerifyIdToken:
    def test_verify_id_token_delegates_to_auth_module_with_app(
        self,
        mock_firebase_admin: MagicMock,
        mock_credentials: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        settings = make_settings()
        admin = FirebaseAdmin(settings)
        mock_auth.verify_id_token.return_value = {"uid": "abc123"}

        claims = admin.verify_id_token("some-id-token")

        mock_auth.verify_id_token.assert_called_once_with(
            "some-id-token", app=admin._app
        )
        assert claims == {"uid": "abc123"}


class TestGetFirebaseAdmin:
    def test_returns_same_instance_across_calls(
        self,
        mock_firebase_admin: MagicMock,
        mock_credentials: MagicMock,
        mocker: pytest_mock.MockerFixture,  # noqa: F821
    ) -> None:
        mocker.patch("app.core.firebase.get_settings", return_value=make_settings())

        first = get_firebase_admin()
        second = get_firebase_admin()

        assert first is second
