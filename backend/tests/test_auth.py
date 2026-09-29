import pytest

import app.main  # noqa: F401 - register all SQLAlchemy models before mapper configuration

from app.services.auth import hash_password, normalize_email, verify_password


def test_password_hash_round_trip():
    password = "correct-horse-battery-staple"
    password_hash = hash_password(password)

    assert password_hash.startswith("pbkdf2_sha256$")
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_password_hashes_are_unique():
    password = "correct-horse-battery-staple"

    first = hash_password(password)
    second = hash_password(password)

    assert first != second
    assert verify_password(password, first)
    assert verify_password(password, second)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("User@Example.COM", "user@example.com"),
        ("  user@example.com  ", "user@example.com"),
    ],
)
def test_normalize_email(raw: str, expected: str):
    assert normalize_email(raw) == expected


from datetime import datetime, timedelta, timezone

from app.models.email_verification_token import EmailVerificationToken
from app.models.organization_membership import OrganizationMembership
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_session import UserSession


def test_email_verification_token_model():
    user = User(email="test@example.com", password_hash=hash_password("a" * 12))
    token = EmailVerificationToken(
        user=user,
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    assert token.user is user
    assert token.used_at is None
    assert len(token.token_hash) == 64
