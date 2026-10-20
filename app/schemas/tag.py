from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TagUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)

    @field_validator("name", mode="before")
    @classmethod
    def _normalize_name(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
