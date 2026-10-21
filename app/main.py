from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.session import engine
from sqlalchemy import text
from app.api.v1.router import api_router
from app.workers.celery_app import celery_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    yield


app = FastAPI(
    title="Bookmark Manager",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
