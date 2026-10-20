from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services.tag import TagAlreadyExistsError, TagNotFoundError, TagService

router = APIRouter(prefix="/tags", tags=["tags"])


def get_tag_service(session: Annotated[AsyncSession, Depends(get_db)]) -> TagService:
    return TagService(session=session)


TagSvc = Annotated[TagService, Depends(get_tag_service)]


@router.get("", response_model=list[TagRead])
async def get_all_tags(user: CurrentUser, svc: TagSvc):
    return await svc.get_all(user_id=user.id)


@router.get("/{tag_id}", response_model=TagRead)
async def get_tag(user: CurrentUser, svc: TagSvc, tag_id: UUID):
    try:
        return await svc.get_by_id(user_id=user.id, tag_id=tag_id)
    except TagNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(user: CurrentUser, svc: TagSvc, payload: TagCreate):
    try:
        return await svc.create(user_id=user.id, data=payload)
    except TagAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{tag_id}", response_model=TagRead)
async def update_tag(user: CurrentUser, svc: TagSvc, payload: TagUpdate, tag_id: UUID):
    try:
        return await svc.update(user_id=user.id, tag_id=tag_id, data=payload)
    except TagNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TagAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(user: CurrentUser, svc: TagSvc, tag_id: UUID):
    try:
        await svc.delete(user_id=user.id, tag_id=tag_id)
    except TagNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
