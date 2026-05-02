from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import ApiKey


@dataclass
class ApiKeyContext:
    key: str
    role: str


def ensure_role(ctx: ApiKeyContext, *allowed_roles: str) -> None:
    if ctx.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient role. Allowed roles: {', '.join(allowed_roles)}",
        )


async def require_api_key(
    x_api_key: str | None = Header(None),
    api_key: str | None = Query(None, alias="api_key"),
    db: AsyncSession = Depends(get_session),
) -> str:
    ctx = await require_api_key_context(x_api_key=x_api_key, api_key=api_key, db=db)
    return ctx.key


async def require_api_key_context(
    x_api_key: str | None = Header(None),
    api_key: str | None = Query(None, alias="api_key"),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyContext:
    key = x_api_key or api_key
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass X-API-Key header or ?api_key= query param.",
        )
    result = await db.execute(
        select(ApiKey).where(ApiKey.key == key, ApiKey.active == True)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    return ApiKeyContext(key=obj.key, role=obj.role or "admin")
