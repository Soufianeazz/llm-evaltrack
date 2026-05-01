import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import DemoRequest

router = APIRouter(prefix="/demo-request", tags=["demo"])


class DemoRequestSubmit(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=10, max_length=4000)
    plan: str | None = Field(default=None, max_length=64)
    source: str = Field(default="website", max_length=128)


@router.post("")
async def create_demo_request(
    body: DemoRequestSubmit,
    db: AsyncSession = Depends(get_session),
):
    entry = DemoRequest(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        email=str(body.email).strip().lower(),
        company=body.company.strip(),
        plan=(body.plan or "").strip() or None,
        message=body.message.strip(),
        source=body.source.strip() or "website",
        timestamp=time.time(),
    )
    db.add(entry)
    await db.commit()
    return {"status": "ok", "id": entry.id}


@router.get("")
async def list_demo_requests(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    import os

    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        select(DemoRequest).order_by(DemoRequest.timestamp.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "email": r.email,
            "company": r.company,
            "plan": r.plan,
            "message": r.message,
            "source": r.source,
            "timestamp": r.timestamp,
        }
        for r in rows
    ]
