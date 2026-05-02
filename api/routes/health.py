import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session

router = APIRouter()


@router.get("/healthz")
async def healthz():
    """Liveness probe: process is up."""
    return {"status": "ok", "ts": time.time()}


@router.get("/readyz")
async def readyz(db: AsyncSession = Depends(get_session)):
    """Readiness probe: process + database are ready."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "checks": {"database": "ok"}, "ts": time.time()}


@router.get("/health")
async def health_detail(db: AsyncSession = Depends(get_session)):
    """Detailed health payload for internal monitoring."""
    started = time.time()
    await db.execute(text("SELECT 1"))
    latency_ms = round((time.time() - started) * 1000, 2)
    return {
        "status": "ok",
        "checks": {
            "database": {
                "status": "ok",
                "latency_ms": latency_ms,
            },
        },
        "ts": time.time(),
    }
