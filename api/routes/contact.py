import os
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import ContactRequest

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactSubmit(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    plan: str = ""
    message: str = ""
    source: str = "landing"


@router.post("")
async def submit_contact(body: ContactSubmit, db: AsyncSession = Depends(get_session)):
    entry = ContactRequest(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        company=body.company or None,
        plan=body.plan or None,
        message=body.message or None,
        source=body.source,
        timestamp=time.time(),
    )
    db.add(entry)
    await db.commit()
    return {"status": "ok"}


@router.get("")
async def list_contacts(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token or token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")
    result = await db.execute(
        select(ContactRequest).order_by(ContactRequest.timestamp.desc())
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "email": e.email,
            "company": e.company,
            "plan": e.plan,
            "message": e.message,
            "source": e.source,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]
