"""
Self-host instance registry — customer-side endpoints for the Deploy flow.

A customer signs up on agentlens.one → gets a tenant API key → deploys an
AgentLens container on their own infrastructure → registers that deployment
here so we know it exists. NO customer data is sent here, only metadata
(label, registered_at, optional healthcheck URL).

Authentication: tenant API key (same key used for ingest). The customer is
authenticated as the owner of any instance whose api_key matches theirs.
"""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import ApiKeyContext, require_api_key_context
from storage.database import get_session
from storage.models import AuditLog, SelfHostInstance

router = APIRouter(prefix="/portal/instances")


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return key or ""
    return f"{key[:6]}…{key[-4:]}"


async def _audit(db: AsyncSession, action: str, detail: str) -> None:
    db.add(AuditLog(id=str(uuid.uuid4()), action=action, detail=detail, timestamp=time.time()))
    await db.commit()


class RegisterPayload(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    pilot: bool = False
    healthcheck_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=2000)


class UpdatePayload(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    healthcheck_url: HttpUrl | None = None
    notes: str | None = Field(default=None, max_length=2000)


def _serialise(inst: SelfHostInstance) -> dict:
    return {
        "id": inst.id,
        "label": inst.label,
        "pilot": bool(inst.pilot),
        "registered_at": inst.registered_at,
        "last_pinged_at": inst.last_pinged_at,
        "healthcheck_url": inst.healthcheck_url,
        "notes": inst.notes,
        "api_key_masked": _mask_key(inst.api_key),
    }


@router.post("")
async def register_instance(
    payload: RegisterPayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    """Customer marks 'I deployed my instance' on the Deploy page."""
    inst = SelfHostInstance(
        id=str(uuid.uuid4()),
        api_key=ctx.key,
        label=payload.label.strip(),
        pilot=bool(payload.pilot),
        registered_at=time.time(),
        healthcheck_url=str(payload.healthcheck_url) if payload.healthcheck_url else None,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(inst)
    await db.commit()
    await _audit(
        db,
        "self_host_instance_registered",
        f"instance_id={inst.id} label={inst.label} pilot={inst.pilot} api_key={_mask_key(ctx.key)}",
    )
    return _serialise(inst)


@router.get("")
async def list_instances(
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    """List all instances registered under the current tenant key."""
    result = await db.execute(
        select(SelfHostInstance)
        .where(SelfHostInstance.api_key == ctx.key)
        .order_by(SelfHostInstance.registered_at.desc())
    )
    return {"instances": [_serialise(i) for i in result.scalars().all()]}


@router.get("/{instance_id}")
async def get_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    result = await db.execute(
        select(SelfHostInstance).where(
            SelfHostInstance.id == instance_id, SelfHostInstance.api_key == ctx.key
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return _serialise(inst)


@router.patch("/{instance_id}")
async def update_instance(
    instance_id: str,
    payload: UpdatePayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    result = await db.execute(
        select(SelfHostInstance).where(
            SelfHostInstance.id == instance_id, SelfHostInstance.api_key == ctx.key
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    if payload.label is not None:
        inst.label = payload.label.strip()
    if payload.healthcheck_url is not None:
        inst.healthcheck_url = str(payload.healthcheck_url)
    if payload.notes is not None:
        inst.notes = payload.notes.strip() or None

    await db.commit()
    await _audit(db, "self_host_instance_updated", f"instance_id={inst.id}")
    return _serialise(inst)


@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
):
    result = await db.execute(
        select(SelfHostInstance).where(
            SelfHostInstance.id == instance_id, SelfHostInstance.api_key == ctx.key
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    await db.delete(inst)
    await db.commit()
    await _audit(db, "self_host_instance_deleted", f"instance_id={instance_id}")
    return {"deleted": True, "id": instance_id}
