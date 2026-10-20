from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.auth import LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.auth_service import AuthError, AuthService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: Annotated[AsyncSession, Depends(get_db)]) -> AuthService:
    return AuthService(session)


AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, svc: AuthSvc) -> UserRead:
    try:
        user = await svc.signup(data=payload)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: UserLogin, svc: AuthSvc) -> TokenPair:
    try:
        return await svc.login(email=payload.email, password=payload.password)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, svc: AuthSvc) -> TokenPair:
    try:
        return await svc.refresh(payload.refresh_token)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, svc: AuthSvc) -> None:
    await svc.logout(payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
