import os
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
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


async def _notify_demo_request(payload: dict) -> None:
    webhook_url = os.environ.get("DEMO_REQUEST_WEBHOOK_URL", "").strip()
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    notify_email = os.environ.get("DEMO_REQUEST_NOTIFY_EMAIL", "").strip()
    from_email = os.environ.get("DEMO_REQUEST_FROM_EMAIL", "AgentLens <noreply@agentlens.one>").strip()

    async with httpx.AsyncClient(timeout=10) as client:
        if webhook_url:
            try:
                await client.post(
                    webhook_url,
                    json={
                        "event": "demo_request_created",
                        "timestamp": payload["timestamp"],
                        "lead": payload,
                    },
                )
            except Exception:
                # Non-blocking best-effort notification.
                pass

        if resend_api_key and notify_email:
            try:
                subject = f"New demo request: {payload['company']} ({payload['plan'] or 'unspecified plan'})"
                body = (
                    f"New AgentLens demo request\n\n"
                    f"Name: {payload['name']}\n"
                    f"Email: {payload['email']}\n"
                    f"Company: {payload['company']}\n"
                    f"Plan: {payload['plan'] or 'n/a'}\n"
                    f"Source: {payload['source']}\n"
                    f"Timestamp: {payload['timestamp']}\n\n"
                    f"Message:\n{payload['message']}\n"
                )
                await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_api_key}"},
                    json={
                        "from": from_email,
                        "to": [notify_email],
                        "subject": subject,
                        "text": body,
                    },
                )
            except Exception:
                # Non-blocking best-effort notification.
                pass


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

    payload = {
        "id": entry.id,
        "name": entry.name,
        "email": entry.email,
        "company": entry.company,
        "plan": entry.plan,
        "message": entry.message,
        "source": entry.source,
        "timestamp": entry.timestamp,
    }
    await _notify_demo_request(payload)
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
