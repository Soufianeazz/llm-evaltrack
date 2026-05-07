import hashlib
import hmac
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_auth import require_admin_token
from api.customer_access import evaluate_customer_access
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
    plan: str = Field(default="pilot", pattern="^(pilot|starter|team|scale)$")
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


@router.post("/signup")
async def signup(payload: SignupPayload, db: AsyncSession = Depends(get_session)):
    email = payload.email.strip().lower()
    result = await db.execute(select(CustomerAccount).where(CustomerAccount.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists for this email")

    now = time.time()
    account = CustomerAccount(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=_hash_password(payload.password),
        name=(payload.name or "").strip() or None,
        company=(payload.company or "").strip() or None,
        status="pending",
        access_state="pending",
        created_at=now,
    )
    db.add(account)
    await db.commit()
    await _audit(
        db,
        "customer_signup",
        f"account_id={account.id} email={account.email} company={account.company or '-'}",
    )
    return {
        "status": "pending_approval",
        "message": "Signup submitted. Access will be enabled after approval.",
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
    key_value = account.api_key
    if not key_value:
        key_value = "al_" + secrets.token_urlsafe(24)
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
    else:
        key_result = await db.execute(select(ApiKey).where(ApiKey.key == key_value))
        key_obj = key_result.scalar_one_or_none()
        if key_obj:
            key_obj.active = True
            key_obj.plan = payload.plan
            key_obj.role = payload.role

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
