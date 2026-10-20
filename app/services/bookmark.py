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
    def __init__(self, session: AsyncSession):
        self.session = session

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
        stmt = select(Bookmark).where(Bookmark.user_id == user_id,
                                      Bookmark.id == bookmark_id).options(selectinload(Bookmark.tags))

        bookmark = await self.session.scalar(statement=stmt)
        if bookmark is None:
            raise BookmarkNotFound(str(bookmark_id))

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

        return bookmark

    async def update(self, user_id: UUID, bookmark_id: UUID, data: BookmarkUpdate) -> Bookmark:
        bookmark = await self.get(user_id=user_id, bookmark_id=bookmark_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "tag_names":
                bookmark.tags = await self._resolve_tags(user_id, value or [])
            else:
                setattr(bookmark, field, value)
        await self.session.commit()
        await self.session.refresh(bookmark, attribute_names=["tags"])
        return bookmark

    async def delete(self, user_id: UUID, bookmark_id: UUID) -> None:
        bookmark = await self.get(user_id, bookmark_id)
        await self.session.delete(bookmark)
        await self.session.commit()

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
