from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import ApiKey


async def require_api_key(
    x_api_key: str | None = Header(None),
    api_key: str | None = Query(None, alias="api_key"),
    db: AsyncSession = Depends(get_session),
) -> str:
    key = x_api_key or api_key
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass X-API-Key header or ?api_key= query param.",
        )
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == key, ApiKey.active == True)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    return key
