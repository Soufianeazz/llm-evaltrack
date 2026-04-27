import os
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import ApiKey

router = APIRouter(prefix="/admin")


def _require_admin(token: str | None):
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token or token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


class CreateKeyPayload(BaseModel):
    label: str
    plan: str = "pilot"


@router.post("/api-keys")
async def create_api_key(
    payload: CreateKeyPayload,
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    key = "al_" + secrets.token_urlsafe(24)
    obj = ApiKey(key=key, label=payload.label, plan=payload.plan, created_at=time.time())
    db.add(obj)
    await db.commit()
    return {"key": key, "label": payload.label, "plan": payload.plan}


@router.get("/api-keys")
async def list_api_keys(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        {"key": k.key, "label": k.label, "plan": k.plan, "active": k.active, "created_at": k.created_at}
        for k in keys
    ]


@router.delete("/api-keys/{key}")
async def deactivate_api_key(
    key: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Key not found")
    obj.active = False
    await db.commit()
    return {"deactivated": key}
