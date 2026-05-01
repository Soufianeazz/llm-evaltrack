import os
import time
import uuid
import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
import httpx
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.limiter import limiter
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
    website: str | None = Field(default=None, max_length=256)


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


def _require_admin(token: str) -> None:
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("")
@limiter.limit("6/minute")
async def create_demo_request(
    request: Request,
    body: DemoRequestSubmit,
    db: AsyncSession = Depends(get_session),
):
    # Honeypot: hidden field should remain empty for real users.
    if body.website and body.website.strip():
        # Return success-like response to avoid teaching bots.
        return {"status": "ok"}

    email = str(body.email).strip().lower()
    ten_minutes_ago = time.time() - 600
    recent = await db.execute(
        select(DemoRequest).where(
            DemoRequest.email == email,
            DemoRequest.timestamp >= ten_minutes_ago,
        )
    )
    if recent.scalar_one_or_none():
        return {"status": "ok", "deduplicated": True}

    entry = DemoRequest(
        id=str(uuid.uuid4()),
        name=body.name.strip(),
        email=email,
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
    _require_admin(token)

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


@router.get("/weekly")
async def list_weekly_demo_requests(
    token: str = Query(...),
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    cutoff = time.time() - days * 86400
    result = await db.execute(
        select(DemoRequest)
        .where(DemoRequest.timestamp >= cutoff)
        .order_by(DemoRequest.timestamp.desc())
    )
    rows = result.scalars().all()
    return {
        "days": days,
        "count": len(rows),
        "items": [
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
        ],
    }


@router.get("/weekly.csv")
async def download_weekly_demo_requests_csv(
    token: str = Query(...),
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_session),
):
    from fastapi.responses import Response

    _require_admin(token)
    cutoff = time.time() - days * 86400
    result = await db.execute(
        select(DemoRequest)
        .where(DemoRequest.timestamp >= cutoff)
        .order_by(DemoRequest.timestamp.desc())
    )
    rows = result.scalars().all()

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "name", "email", "company", "plan", "source", "timestamp", "message"])
    for r in rows:
        writer.writerow([r.id, r.name, r.email, r.company, r.plan or "", r.source or "", r.timestamp, r.message])

    content = buffer.getvalue()
    filename = f"agentlens_demo_requests_last_{days}_days.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )


@router.post("/notify-test")
async def notify_test(
    token: str = Query(...),
):
    _require_admin(token)
    webhook_url = os.environ.get("DEMO_REQUEST_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return {"status": "not_configured", "detail": "DEMO_REQUEST_WEBHOOK_URL is empty"}

    payload = {
        "id": "test-" + str(uuid.uuid4())[:8],
        "name": "AgentLens Test",
        "email": "test@example.com",
        "company": "AgentLens",
        "plan": "team",
        "message": "This is a manual notification test.",
        "source": "notify-test",
        "timestamp": time.time(),
    }
    await _notify_demo_request(payload)
    return {"status": "ok", "detail": "Notification test sent"}
