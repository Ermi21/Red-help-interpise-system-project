import pytest

from app.auth.jwt_handler import create_access_token, decode_access_token
from app.auth.password import hash_password, verify_password
from app.auth.rbac import Role, role_satisfies
from app.utils.exceptions import AuthenticationError


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", hashed) is False


class TestJwt:
    def test_round_trip(self):
        token = create_access_token(subject="user-123", role="analyst")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "analyst"

    def test_invalid_token_raises(self):
        with pytest.raises(AuthenticationError):
            decode_access_token("not-a-real-token")


class TestRbac:
    def test_admin_satisfies_viewer_requirement(self):
        assert role_satisfies("admin", Role.VIEWER) is True

    def test_viewer_does_not_satisfy_admin_requirement(self):
        assert role_satisfies("viewer", Role.ADMIN) is False

    def test_unknown_role_never_satisfies(self):
        assert role_satisfies("not-a-role", Role.VIEWER) is False
