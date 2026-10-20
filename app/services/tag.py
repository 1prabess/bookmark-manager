from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


class TagError(Exception):
    """Base exception for tag-related errors."""


class TagNotFoundError(TagError):
    pass


class TagAlreadyExistsError(TagError):
    pass


class TagService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: UUID, data: TagCreate) -> Tag:
        existing = await self.session.scalar(select(Tag).where(Tag.name == data.name, Tag.user_id == user_id))
        if existing is not None:
            raise TagAlreadyExistsError("Tag already exists")

        tag = Tag(
            user_id=user_id,
            name=data.name
        )

        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def update(self, user_id: UUID, tag_id: UUID, data: TagUpdate) -> Tag:
        tag = await self.session.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
        if tag is None:
            raise TagNotFoundError("Tag not found")

        existing = await self.session.scalar(
            select(Tag).where(
                Tag.user_id == user_id,
                Tag.name == data.name,
                Tag.id != tag_id,
            )
        )

        if existing is not None:
            raise TagAlreadyExistsError("Tag already exists")

        tag.name = data.name

        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def delete(self, user_id: UUID, tag_id: UUID) -> None:
        tag = await self.session.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
        if tag is None:
            raise TagNotFoundError("Tag not found")

        await self.session.delete(tag)
        await self.session.commit()

    async def get_all(self, user_id: UUID) -> list[Tag]:
        result = await self.session.scalars(
            select(Tag)
            .where(Tag.user_id == user_id)
            .order_by(Tag.name)
        )
        return list(result.all())

    async def get_by_id(self, user_id: UUID, tag_id: UUID) -> Tag:
        tag = await self.session.scalar(
            select(Tag).where(
                Tag.id == tag_id,
                Tag.user_id == user_id,
            )
        )

        if tag is None:
            raise TagNotFoundError("Tag not found")

        return tag
