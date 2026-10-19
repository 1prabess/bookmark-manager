from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from app.core.config import settings

from passlib.context import CryptContext
import hashlib
import secrets
import jwt


pwd_context = CryptContext(schemes=["bcrypt"], deprecated=["auto"])


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_refresh_token_value() -> tuple[str, datetime]:
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + \
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    return raw, expires_at


def create_access_token(subject: str | UUID, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
        "jti": str(uuid4()),
        **(extra or {}),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=settings.JWT_ALGORITHM
        )
    except jwt.PyJWTError:
        return None
