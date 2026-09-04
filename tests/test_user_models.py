from app.models.user import (
    ProviderType,
    UserProfile,
    UserRole,
)


def test_traveler_default_role():
    user = UserProfile(
        uid="123",
    )

    assert user.roles == {UserRole.TRAVELER}


def test_provider_profile():
    user = UserProfile(
        uid="123",
        email="test@example.com",
        roles={UserRole.PROVIDER},
        provider_type=ProviderType.TOUR_GUIDE,
        cities_served=["Lisbon"],
    )

    assert user.provider_type == (ProviderType.TOUR_GUIDE)


def test_dual_role_user():
    user = UserProfile(
        uid="123",
        email="test@example.com",
        roles={
            UserRole.TRAVELER,
            UserRole.PROVIDER,
        },
    )

    assert len(user.roles) == 2
