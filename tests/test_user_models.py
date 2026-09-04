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


def test_user_can_have_multiple_roles():
    user = UserProfile(
        uid="123",
        roles={
            UserRole.TRAVELER,
            UserRole.PROVIDER,
        },
        provider_type=ProviderType.TOUR_GUIDE,
    )

    assert UserRole.TRAVELER in user.roles
    assert UserRole.PROVIDER in user.roles
