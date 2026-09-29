import pytest

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
