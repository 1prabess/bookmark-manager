from sqlalchemy import Table, Column, ForeignKey
from app.db.base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


bookmark_tags = Table(
    "bookmark_tags",
    Base.metadata,
    Column(
        "bookmark_id",
        PG_UUID(as_uuid=True),
        ForeignKey("bookmarks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
