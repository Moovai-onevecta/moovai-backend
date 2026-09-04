from app.deps.auth import AuthenticatedUser


class FakeFirebase:
    def verify_id_token(self, token: str):
        return {
            "uid": "user_123",
            "email": "test@example.com",
            "role": "traveler",
        }


def test_authenticated_user_model():
    user = AuthenticatedUser(
        uid="user_123",
        email="test@example.com",
        claims={"role": "traveler"},
    )

    assert user.uid == "user_123"
    assert user.claims["role"] == "traveler"