import hashlib
import hmac
import os
import secrets
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_auth import require_admin_token
from api.customer_access import evaluate_customer_access
from api.limiter import limiter
from storage.database import get_session
from storage.models import ApiKey, AuditLog, CustomerAccount

router = APIRouter(prefix="/auth")
admin_router = APIRouter(prefix="/admin/customers")

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ROUNDS = 210_000


class SignupPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    name: str | None = Field(default=None, max_length=160)
    company: str | None = Field(default=None, max_length=200)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ApprovePayload(BaseModel):
    plan: str = Field(default="pilot", pattern="^(pilot|starter|team|scale|enterprise)$")
    trial_days: int = Field(default=14, ge=1, le=365)
    role: str = Field(default="admin", pattern="^(admin|analyst|read_only)$")


class SubscriptionStatusPayload(BaseModel):
    subscription_status: str = Field(
        pattern="^(active|trialing|past_due|canceled|unpaid|paused|incomplete|incomplete_expired)$"
    )


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ROUNDS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ROUNDS}${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, rounds_s, salt, expected = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        rounds = int(rounds_s)
    except Exception:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        rounds,
    ).hex()
    return hmac.compare_digest(digest, expected)


async def _audit(db: AsyncSession, action: str, detail: str) -> None:
    db.add(AuditLog(id=str(uuid.uuid4()), action=action, detail=detail, timestamp=time.time()))
    await db.commit()


async def _send_welcome_email(user_email: str, api_key: str, name: str | None) -> None:
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_email = os.environ.get("SIGNUP_NOTIFY_FROM_EMAIL", "AgentLens <noreply@agentlens.one>").strip()
    notify_email = os.environ.get("SIGNUP_NOTIFY_EMAIL", "").strip()
    first_name = (name or "").split()[0] if name else "there"

    welcome_body = (
        f"Hi {first_name},\n\n"
        "Your AgentLens account is ready. Here's your API key:\n\n"
        f"  {api_key}\n\n"
        "Get your first trace in 2 minutes:\n\n"
        "  pip install agentlens-monitor\n\n"
        "  import agentlens\n"
        f'  agentlens.init(api_key="{api_key}")\n'
        "  agentlens.patch_openai()  # or patch_anthropic()\n\n"
        "That's it — every LLM call is now tracked automatically.\n\n"
        "Full quickstart: https://www.agentlens.one/app/start\n"
        "Dashboard: https://www.agentlens.one/dashboard\n\n"
        "— Soufiane, AgentLens founder\n"
        "  Reply to this email anytime.\n"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        if resend_api_key:
            try:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {resend_api_key}"},
                    json={
                        "from": from_email,
                        "to": [user_email],
                        "subject": "Your AgentLens API key is ready",
                        "text": welcome_body,
                    },
                )
            except Exception:
                pass

            if notify_email:
                try:
                    await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {resend_api_key}"},
                        json={
                            "from": from_email,
                            "to": [notify_email],
                            "subject": f"New signup: {user_email}",
                            "text": f"New AgentLens signup\n\nEmail: {user_email}\nAPI key: {api_key}\n",
                        },
                    )
                except Exception:
                    pass


@router.post("/signup")
@limiter.limit("5/minute")
async def signup(request: Request, payload: SignupPayload, db: AsyncSession = Depends(get_session)):
    email = payload.email.strip().lower()

    now = time.time()
    trial_days = 14
    api_key_value = "al_" + secrets.token_urlsafe(24)

    account = CustomerAccount(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=_hash_password(payload.password),
        name=(payload.name or "").strip() or None,
        company=(payload.company or "").strip() or None,
        status="approved",
        access_state="trialing",
        plan="starter",
        api_key=api_key_value,
        trial_ends_at=now + trial_days * 86400,
        approved_at=now,
        approved_by="auto",
        created_at=now,
    )
    db.add(account)
    db.add(
        ApiKey(
            key=api_key_value,
            label=account.company or account.email,
            plan="starter",
            role="admin",
            created_at=now,
            active=True,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Account already exists for this email")

    await _send_welcome_email(account.email, api_key_value, account.name)
    await _audit(
        db,
        "customer_signup",
        f"account_id={account.id} email={account.email} company={account.company or '-'} auto_approved=true",
    )
    return {
        "status": "approved",
        "api_key": api_key_value,
        "plan": "starter",
        "trial_ends_at": account.trial_ends_at,
        "dashboard_url": "/app/start",
    }


@router.post("/login")
async def login(payload: LoginPayload, db: AsyncSession = Depends(get_session)):
    email = payload.email.strip().lower()
    result = await db.execute(select(CustomerAccount).where(CustomerAccount.email == email))
    account = result.scalar_one_or_none()
    if not account or not _verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if (account.status or "pending") != "approved":
        raise HTTPException(status_code=403, detail=f"Account not approved ({account.status})")

    allowed, reason = evaluate_customer_access(account)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Access blocked: {reason}")

    if not account.api_key:
        raise HTTPException(status_code=403, detail="No tenant API key assigned")

    key_result = await db.execute(select(ApiKey).where(ApiKey.key == account.api_key))
    key_obj = key_result.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=403, detail="Assigned API key does not exist")
    if not key_obj.active:
        key_obj.active = True

    account.last_login_at = time.time()
    await db.commit()
    return {
        "status": "ok",
        "api_key": key_obj.key,
        "plan": account.plan,
        "access_state": account.access_state,
        "dashboard_url": "/dashboard",
    }


@admin_router.get("")
async def list_customers(
    status: str | None = Query(None),
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    query = select(CustomerAccount).order_by(CustomerAccount.created_at.desc())
    if status:
        query = query.where(CustomerAccount.status == status)
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": a.id,
            "email": a.email,
            "name": a.name,
            "company": a.company,
            "status": a.status,
            "access_state": a.access_state,
            "plan": a.plan,
            "api_key": a.api_key,
            "trial_ends_at": a.trial_ends_at,
            "stripe_customer_id": a.stripe_customer_id,
            "stripe_subscription_id": a.stripe_subscription_id,
            "subscription_status": a.subscription_status,
            "created_at": a.created_at,
            "approved_at": a.approved_at,
            "last_login_at": a.last_login_at,
        }
        for a in items
    ]


@admin_router.post("/{account_id}/approve")
async def approve_customer(
    account_id: str,
    payload: ApprovePayload,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(CustomerAccount).where(CustomerAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Customer account not found")

    now = time.time()
    old_key = account.api_key

    # Always generate a fresh key on (re-)approval so old keys can't persist with stale plans
    key_value = "al_" + secrets.token_urlsafe(24)

    # Deactivate the old key if one exists
    if old_key and old_key != key_value:
        old_key_result = await db.execute(select(ApiKey).where(ApiKey.key == old_key))
        old_key_obj = old_key_result.scalar_one_or_none()
        if old_key_obj:
            old_key_obj.active = False

    db.add(
        ApiKey(
            key=key_value,
            label=account.company or account.email,
            plan=payload.plan,
            role=payload.role,
            created_at=now,
            active=True,
        )
    )

    account.api_key = key_value
    account.status = "approved"
    account.access_state = "trialing"
    account.plan = payload.plan
    account.trial_ends_at = now + payload.trial_days * 86400
    account.subscription_status = None
    account.approved_at = now
    account.approved_by = "admin_token"
    await db.commit()
    await _audit(
        db,
        "customer_approved",
        (
            f"account_id={account.id} email={account.email} plan={payload.plan} "
            f"trial_days={payload.trial_days} api_key={key_value[:8]}..."
        ),
    )
    return {
        "approved": True,
        "account_id": account.id,
        "email": account.email,
        "api_key": key_value,
        "trial_ends_at": account.trial_ends_at,
    }


@admin_router.post("/{account_id}/suspend")
async def suspend_customer(
    account_id: str,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(CustomerAccount).where(CustomerAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Customer account not found")

    account.status = "suspended"
    account.access_state = "suspended"
    if account.api_key:
        key_result = await db.execute(select(ApiKey).where(ApiKey.key == account.api_key))
        key_obj = key_result.scalar_one_or_none()
        if key_obj:
            key_obj.active = False
    await db.commit()
    await _audit(db, "customer_suspended", f"account_id={account.id} email={account.email}")
    return {"suspended": True, "account_id": account.id}


@admin_router.post("/{account_id}/subscription-status")
async def set_subscription_status(
    account_id: str,
    payload: SubscriptionStatusPayload,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(CustomerAccount).where(CustomerAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Customer account not found")

    new_status = payload.subscription_status.lower()
    account.subscription_status = new_status
    if new_status in {"active", "trialing"}:
        account.access_state = new_status
    elif new_status in {"past_due", "canceled", "unpaid", "paused", "incomplete", "incomplete_expired"}:
        account.access_state = "past_due" if new_status == "past_due" else "canceled"

    if account.api_key:
        key_result = await db.execute(select(ApiKey).where(ApiKey.key == account.api_key))
        key_obj = key_result.scalar_one_or_none()
        if key_obj:
            allowed, _ = evaluate_customer_access(account)
            key_obj.active = allowed

    await db.commit()
    await _audit(
        db,
        "customer_subscription_status_changed",
        f"account_id={account.id} status={new_status}",
    )
    return {
        "updated": True,
        "account_id": account.id,
        "subscription_status": account.subscription_status,
        "access_state": account.access_state,
    }
