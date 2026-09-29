import hashlib
import hmac
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession


PASSWORD_ITERATIONS = 310_000
SESSION_DAYS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256$" + str(PASSWORD_ITERATIONS) + "$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_session(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    db.add(session)
    db.commit()
    return raw_token


def get_user_from_session(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if not session or session.expires_at <= datetime.now(timezone.utc):
        if session:
            db.delete(session)
            db.commit()
        return None
    if not session.user.is_active:
        return None
    return session.user


def cleanup_expired_sessions(db: Session) -> int:
    now = datetime.now(timezone.utc)
    sessions = db.scalars(
        select(UserSession).where(UserSession.expires_at <= now)
    ).all()
    for session in sessions:
        db.delete(session)
    if sessions:
        db.commit()
    return len(sessions)


def delete_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
    if session:
        db.delete(session)
        db.commit()
