from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token_value, hash_password, hash_refresh_token, verify_password
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate
from app.workers.tasks.email import hash_reset_token, queue_send_welcome, generate_token,  queue_send_password_reset


class AuthError(Exception):
    """Service-level auth failure. Router maps this to a status code."""


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def signup(self, data: UserCreate) -> User:
        result = await self.session.execute(
            select(User).where(User.email == data.email)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            raise AuthError("Email already registered")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password)
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        queue_send_welcome(to_email=user.email)
        return user

    async def login(self, *, email: str, password: str) -> TokenPair:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("User is inactive")

        pair, _ = await self._issue_token_pair(user)
        await self.session.commit()
        return pair

    async def refresh(self, raw_token: str) -> TokenPair:
        token_hash = hash_refresh_token(raw=raw_token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        refresh_token = result.scalar_one_or_none()

        if refresh_token is None:
            raise AuthError("Invalid refresh token")
        if refresh_token.revoked_at is not None:
            raise AuthError("Refresh token revoked")
        if refresh_token.expires_at < datetime.now(timezone.utc):
            raise AuthError("Refresh token expired")

        user = await self.session.get(User, refresh_token.user_id)
        if user is None or not user.is_active:
            raise AuthError("Invalid user")

        new_pair, new_refresh_token = await self._issue_token_pair(user=user)
        refresh_token.revoked_at = datetime.now(timezone.utc)
        refresh_token.replaced_by_id = new_refresh_token.id
        await self.session.commit()

        return new_pair

    async def logout(self, raw_token: str) -> None:
        token_hash = hash_refresh_token(raw_token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token is None:
            raise AuthError("Invalid refresh token")

        if refresh_token.revoked_at is not None:
            return

        refresh_token.revoked_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def forgot_password(self, email: str) -> None:
        user = await self.session.scalar(select(User).where(User.email == email))

        if user is None:
            return

        raw = generate_token()

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

        self.session.add(reset_token)
        await self.session.commit()
        queue_send_password_reset(to_email=email, reset_token=raw)

    async def reset_password(self, raw_token: str, new_password: str):
        token_hash = hash_reset_token(token=raw_token)

        row = await self.session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))

        if row is None or row.used_at is not None or row.expires_at < datetime.now(timezone.utc):
            raise AuthError("Invalid reset token")

        user = await self.session.get(User, row.user_id)
        if user is None or user.is_active is False:
            raise AuthError("Invalid user")

        user.hashed_password = hash_password(new_password)
        row.used_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _issue_token_pair(self, user: User) -> tuple[TokenPair, RefreshToken]:
        access = create_access_token(subject=user.id)
        raw_refresh, expires_at = create_refresh_token_value()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw=raw_refresh),
            expires_at=expires_at
        )

        self.session.add(refresh)
        await self.session.flush()
        pair = TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        return pair, refresh
