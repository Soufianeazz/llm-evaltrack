from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.customer_access import evaluate_customer_access
from storage.database import get_session
from storage.models import ApiKey, CustomerAccount


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
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=403, detail="Invalid API key")

    customer_result = await db.execute(
        select(CustomerAccount).where(CustomerAccount.api_key == obj.key)
    )
    account = customer_result.scalar_one_or_none()
    if account is not None:
        allowed, reason = evaluate_customer_access(account)
        if not allowed:
            if obj.active:
                obj.active = False
                await db.commit()
            raise HTTPException(status_code=403, detail=f"Access blocked: {reason}")
    if not obj.active:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    return ApiKeyContext(key=obj.key, role=obj.role or "admin")
