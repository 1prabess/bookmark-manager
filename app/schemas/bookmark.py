from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, ConfigDict


_TAG_MAX = 20
_TAG_NAME_MIN = 1
_TAG_NAME_MAX = 64


def _normalize_tag_names(value: list[str] | None) -> list[str] | None:
    if value is None:
        return value
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, str):
            continue
        cleaned = raw.strip().lower()
        if not cleaned:
            continue

        if len(cleaned) > _TAG_NAME_MAX:
            raise ValueError(
                f"tag '{cleaned[:16]}...' exceeds {_TAG_NAME_MAX} characters"
            )
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


class TagBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class BookmarkBase(BaseModel):
    url: AnyHttpUrl
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    tag_names: list[str] = Field(default_factory=list, max_length=_TAG_MAX)


class BookmarkCreate(BookmarkBase):
    @field_validator("tag_names", mode="before")
    @classmethod
    def _normalize_tags(cls, v: object) -> object:
        return _normalize_tag_names(v)  # type: ignore[arg-type]


class BookmarkUpdate(BaseModel):
    url: AnyHttpUrl | None = Field(default=None)
    title: str | None = Field(default=None,  min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    tag_names: list[str] | None = Field(
        default=None, max_length=_TAG_MAX)

    @field_validator("tag_names", mode="before")
    @classmethod
    def _normalize_tags(cls, v: object) -> object:
        return _normalize_tag_names(v)  # type: ignore[arg-type]


class BookmarkRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    url: str
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[TagBrief] = Field(default_factory=list)
