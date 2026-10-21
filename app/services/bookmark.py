import json
import logging

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Sequence
from uuid import UUID

from app.db.models.bookmark import Bookmark
from app.db.models.tag import Tag
from app.schemas.bookmark import BookmarkCreate, BookmarkUpdate


class BookmarkNotFound(Exception):
    pass


class BookmarkService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session = session
        self.redis = redis

    @staticmethod
    def _cache_key(user_id: UUID, bookmark_id: UUID) -> str:
        return f"bookmark:{user_id}:{bookmark_id}"

    async def list_for_users(self, user_id: UUID, *, tag_name: str | None = None, limit: int = 10, offset: int = 0) -> Sequence[Bookmark]:
        stmt = (
            select(Bookmark)
            .options(selectinload(Bookmark.tags))
            .where(Bookmark.user_id == user_id)
            .order_by(Bookmark.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if tag_name is not None:
            stmt = stmt.join(Bookmark.tags).where(Tag.name == tag_name)
        return (await self.session.scalars(stmt)).all()

    async def get(self, user_id: UUID, bookmark_id: UUID) -> Bookmark:
        cache_key = self._cache_key(user_id=user_id, bookmark_id=bookmark_id)

        cached = await self.redis.get(cache_key)

        if cached is not None:
            data = json.loads(cached)

            bm = Bookmark(
                id=UUID(data["id"]),
                user_id=UUID(data["user_id"]),
                url=data["url"],
                title=data["title"],
                description=data.get("description"),
                created_at=data["created_at"],
                updated_at=data["updated_at"]
            )

            bm.tags = []

            for t in data.get("tags", []):
                tag = Tag(
                    id=UUID(t["id"]),
                    user_id=user_id,
                    name=t["name"],
                )
                bm.tags.append(tag)

            return bm

        stmt = select(Bookmark).where(Bookmark.user_id == user_id,
                                      Bookmark.id == bookmark_id).options(selectinload(Bookmark.tags))

        bookmark = await self.session.scalar(statement=stmt)
        if bookmark is None:
            raise BookmarkNotFound(str(bookmark_id))

        await self._write_cache(user_id=user_id, bookmark=bookmark)

        return bookmark

    async def create(self, user_id: UUID, data: BookmarkCreate) -> Bookmark:
        bookmark = Bookmark(
            user_id=user_id,
            url=str(data.url),
            title=data.title,
            description=data.description,
        )

        if data.tag_names:
            bookmark.tags = await self._resolve_tags(user_id, data.tag_names)
        self.session.add(bookmark)
        await self.session.commit()

        await self._write_cache(user_id=user_id, bookmark=bookmark)

        return bookmark

    async def update(self, user_id: UUID, bookmark_id: UUID, data: BookmarkUpdate) -> Bookmark:
        stmt = (
            select(Bookmark)
            .where(
                Bookmark.user_id == user_id,
                Bookmark.id == bookmark_id,
            )
            .options(selectinload(Bookmark.tags))
        )

        bookmark = await self.session.scalar(stmt)

        if bookmark is None:
            raise BookmarkNotFound(str(bookmark_id))

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "tag_names":
                bookmark.tags = await self._resolve_tags(user_id, value or [])
            else:
                setattr(bookmark, field, value)
        await self.session.commit()
        await self.session.refresh(bookmark)

        await self._write_cache(user_id=user_id, bookmark=bookmark)
        return bookmark

    async def delete(self, user_id: UUID, bookmark_id: UUID) -> None:
        bookmark = await self.get(user_id, bookmark_id)
        await self.session.delete(bookmark)
        await self.session.commit()
        await self.redis.delete(self._cache_key(user_id=user_id, bookmark_id=bookmark.id))

    async def _resolve_tags(self, user_id: UUID, names: list[str]):
        existing = (await self.session.scalars(
            select(Tag).where(Tag.user_id == user_id, Tag.name.in_(names))
        )).all()
        existing_names = {t.name for t in existing}
        missing = [
            Tag(user_id=user_id, name=n)
            for n in names
            if n not in existing_names
        ]
        if missing:
            self.session.add_all(missing)
            await self.session.flush()
        return [*existing, *missing]

    async def _write_cache(self, user_id: UUID, bookmark: Bookmark) -> None:
        tags = []
        for tag in bookmark.tags:
            tags.append({
                "id": str(tag.id),
                "name": tag.name,
                "user_id": str(tag.user_id),
            })

        payload = {
            "id": str(bookmark.id),
            "user_id": str(bookmark.user_id),
            "url": bookmark.url,
            "title": bookmark.title,
            "description": bookmark.description,
            "created_at": bookmark.created_at.isoformat(),
            "updated_at": bookmark.updated_at.isoformat(),
            "tags": tags
        }

        await self.redis.set(
            self._cache_key(user_id=user_id, bookmark_id=bookmark.id),
            json.dumps(payload),
            ex=300
        )
