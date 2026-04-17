import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import WaitlistEntry

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistSubmit(BaseModel):
    email: EmailStr
    source: str = "readme"


@router.post("")
async def join_waitlist(body: WaitlistSubmit, db: AsyncSession = Depends(get_session)):
    entry = WaitlistEntry(
        id=str(uuid.uuid4()),
        email=body.email,
        source=body.source,
        timestamp=time.time(),
    )
    db.add(entry)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"status": "already_registered"}
    return {"status": "ok"}


@router.get("")
async def list_waitlist(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    import os
    if token != os.environ.get("ADMIN_TOKEN", "bugspy-admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(
        select(WaitlistEntry).order_by(WaitlistEntry.timestamp.desc())
    )
    entries = result.scalars().all()
    return [{"email": e.email, "source": e.source, "timestamp": e.timestamp} for e in entries]
