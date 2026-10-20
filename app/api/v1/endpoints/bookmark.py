from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.bookmark import BookmarkCreate, BookmarkRead, BookmarkUpdate
from app.services.bookmark import BookmarkNotFound, BookmarkService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


def get_bookmark_service(
        session: Annotated[AsyncSession, Depends(get_db)]
) -> BookmarkService:
    return BookmarkService(session=session)


BookmarkSvc = Annotated[BookmarkService, Depends(get_bookmark_service)]


@router.get("", response_model=list[BookmarkRead])
async def list_bookmarks(
    user: CurrentUser,
    svc: BookmarkSvc,
    tag: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    return await svc.list_for_users(user_id=user.id, tag_name=tag, limit=limit, offset=offset)


@router.post("", response_model=BookmarkRead)
async def create_bookmark(
    user: CurrentUser,
    svc: BookmarkSvc,
    payload: BookmarkCreate
):
    return await svc.create(user_id=user.id, data=payload)


@router.get("/{bookmark_id}", response_model=BookmarkRead)
async def get_bookmark(
    user: CurrentUser,
    svc: BookmarkSvc,
    bookmark_id: UUID
):
    try:
        return await svc.get(user_id=user.id, bookmark_id=bookmark_id)
    except BookmarkNotFound:
        raise HTTPException(status_code=404, detail="Bookmark not found")


@router.patch("/{bookmark_id}", response_model=BookmarkRead)
async def update_bookmark(
    bookmark_id: UUID,
    payload: BookmarkUpdate,
    user: CurrentUser,
    svc: BookmarkSvc,
):
    try:
        return await svc.update(user.id, bookmark_id, payload)
    except BookmarkNotFound:
        raise HTTPException(status_code=404, detail="Bookmark not found")


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: UUID,
    user: CurrentUser,
    svc: BookmarkSvc,
):
    try:
        return await svc.delete(user_id=user.id, bookmark_id=bookmark_id)
    except BookmarkNotFound:
        raise HTTPException(status_code=404, detail="Bookmark not found")
