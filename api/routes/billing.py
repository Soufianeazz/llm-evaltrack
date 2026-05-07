"""
Stripe billing — checkout sessions for Starter, Team, and Scale plans.
Enterprise redirects to sales contact.
"""
import asyncio
import os
import time
from typing import Any

import httpx
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.customer_access import evaluate_customer_access
from storage.database import get_session
from storage.models import ApiKey, CustomerAccount
router = APIRouter(prefix="/billing")

def _load_stripe_key() -> str:
    return (os.getenv("STRIPE_SECRET_KEY") or os.getenv("stripe_secret_key", "")).strip()


def _load_stripe_webhook_secret() -> str:
    return (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()


def _payment_method_types() -> list[str]:
    """
    Stripe Checkout payment methods for self-serve plans.
    Example env:
      STRIPE_CHECKOUT_PAYMENT_METHODS=card,sepa_debit

    Note:
    - Apple Pay and Google Pay are wallet options on top of `card` and appear
      automatically in Stripe Checkout when domain/account requirements are met.
    """
    raw = (os.getenv("STRIPE_CHECKOUT_PAYMENT_METHODS") or "card,sepa_debit").strip()
    methods = [m.strip().lower() for m in raw.split(",") if m.strip()]
    if not methods:
        return ["card"]
    return methods


def _clean_text(value: Any, max_len: int = 500) -> str:
    if value is None:
        return ""
    return str(value).strip()[:max_len]


async def _notify_billing_event(payload: dict[str, Any]) -> None:
    webhook_url = os.environ.get("BILLING_EVENT_WEBHOOK_URL", "").strip()
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    notify_email = os.environ.get("BILLING_NOTIFY_EMAIL", "").strip()
    from_email = os.environ.get("BILLING_NOTIFY_FROM_EMAIL", "AgentLens Billing <noreply@agentlens.one>").strip()
    event_kind = payload.get("event_kind", "billing_checkout_completed")

    async with httpx.AsyncClient(timeout=10) as client:
        if webhook_url:
            try:
                await client.post(
                    webhook_url,
                    json={
                        "event": event_kind,
                        "timestamp": payload.get("timestamp", time.time()),
                        "billing": payload,
                    },
                )
            except Exception:
                pass

        if resend_api_key and notify_email:
            try:
                if event_kind == "billing_onboarding_submitted":
                    subject = f"Onboarding submitted: {payload.get('plan', 'unknown')} - {payload.get('email', 'no-email')}"
                    body = (
                        "AgentLens onboarding form submitted\n\n"
                        f"Plan: {payload.get('plan', 'n/a')}\n"
                        f"Contract term: {payload.get('contract_term_months', 'n/a')} months\n"
                        f"Billing interval: {payload.get('billing_interval', 'n/a')}\n"
                        f"Customer email: {payload.get('email', 'n/a')}\n"
                        f"Customer name: {payload.get('name', 'n/a')}\n"
                        f"Company: {payload.get('company_name', 'n/a')}\n"
                        f"Website: {payload.get('company_website', 'n/a')}\n"
                        f"Primary use case: {payload.get('use_case', 'n/a')}\n"
                        f"Team size: {payload.get('team_size', 'n/a')}\n"
                        f"Monthly volume expectation: {payload.get('monthly_volume', 'n/a')}\n"
                        f"Technical contact name: {payload.get('technical_contact_name', 'n/a')}\n"
                        f"Technical contact email: {payload.get('technical_contact_email', 'n/a')}\n"
                        f"Preferred kickoff window: {payload.get('kickoff_timeline', 'n/a')}\n"
                        f"Implementation notes: {payload.get('implementation_notes', 'n/a')}\n"
                        f"Stripe customer: {payload.get('customer_id', 'n/a')}\n"
                        f"Subscription: {payload.get('subscription_id', 'n/a')}\n"
                        f"Checkout session: {payload.get('checkout_session_id', 'n/a')}\n"
                        f"Timestamp: {payload.get('timestamp', 'n/a')}\n"
                    )
                else:
                    subject = f"New subscription: {payload.get('plan', 'unknown')} - {payload.get('email', 'no-email')}"
                    body = (
                        "New AgentLens subscription purchase\n\n"
                        f"Plan: {payload.get('plan', 'n/a')}\n"
                        f"Contract term: {payload.get('contract_term_months', 'n/a')} months\n"
                        f"Billing interval: {payload.get('billing_interval', 'n/a')}\n"
                        f"Email: {payload.get('email', 'n/a')}\n"
                        f"Name: {payload.get('name', 'n/a')}\n"
                        f"Amount: {payload.get('amount_total', 'n/a')} {payload.get('currency', 'n/a')}\n"
                        f"Stripe customer: {payload.get('customer_id', 'n/a')}\n"
                        f"Subscription: {payload.get('subscription_id', 'n/a')}\n"
                        f"Checkout session: {payload.get('checkout_session_id', 'n/a')}\n"
                        f"Source: {payload.get('source', 'n/a')}\n"
                        f"Timestamp: {payload.get('timestamp', 'n/a')}\n"
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
                pass

PLANS = {
    "starter": {
        "name": "AgentLens Starter",
        "description": "Managed hosting, up to 1M calls/month, 1 project, email support, onboarding call. 12-month commitment, billed monthly.",
        "amount": 29900,  # €299/month
    },
    "team": {
        "name": "AgentLens Team",
        "description": "Up to 10M calls/month, 5 projects, GDPR DPA included, Slack support, monthly review call. 12-month commitment, billed monthly.",
        "amount": 99900,  # €999/month
    },
    "scale": {
        "name": "AgentLens Scale",
        "description": "Up to 50M calls/month, unlimited projects, dedicated cloud instance, 99.9% SLA, security package. 12-month commitment, billed monthly.",
        "amount": 299900,  # €2,999/month
    },
}

ENTERPRISE_EMAIL = "contact@agentlens.one"
CONTRACT_TERM_MONTHS = int((os.getenv("BILLING_CONTRACT_TERM_MONTHS") or "12").strip())


async def _apply_account_access_state(db: AsyncSession, account: CustomerAccount) -> None:
    if account.api_key:
        key_result = await db.execute(select(ApiKey).where(ApiKey.key == account.api_key))
        key_obj = key_result.scalar_one_or_none()
        if key_obj:
            allowed, _ = evaluate_customer_access(account)
            key_obj.active = allowed


async def _sync_checkout_completed_to_account(db: AsyncSession, session: dict[str, Any]) -> None:
    customer_details = session.get("customer_details") or {}
    email = (customer_details.get("email") or session.get("customer_email") or "").strip().lower()
    if not email:
        return

    result = await db.execute(select(CustomerAccount).where(CustomerAccount.email == email))
    account = result.scalar_one_or_none()
    if not account:
        return

    account.stripe_customer_id = session.get("customer") or account.stripe_customer_id
    account.stripe_subscription_id = session.get("subscription") or account.stripe_subscription_id
    account.plan = (session.get("metadata") or {}).get("plan") or account.plan
    payment_status = (session.get("payment_status") or "").lower()
    if payment_status in {"paid", "no_payment_required"}:
        account.subscription_status = "active"
        if (account.status or "pending") == "approved":
            account.access_state = "active"
    await _apply_account_access_state(db, account)


async def _sync_subscription_status_to_account(
    db: AsyncSession,
    customer_id: str | None,
    subscription_id: str | None,
    subscription_status: str,
) -> None:
    if not customer_id and not subscription_id:
        return

    query = select(CustomerAccount)
    if subscription_id:
        query = query.where(CustomerAccount.stripe_subscription_id == subscription_id)
    elif customer_id:
        query = query.where(CustomerAccount.stripe_customer_id == customer_id)
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    if not account:
        return

    if customer_id:
        account.stripe_customer_id = customer_id
    if subscription_id:
        account.stripe_subscription_id = subscription_id
    account.subscription_status = (subscription_status or "").lower() or None

    sub = (subscription_status or "").lower()
    if sub in {"active", "trialing"}:
        account.access_state = sub
    elif sub == "past_due":
        account.access_state = "past_due"
    elif sub in {"canceled", "unpaid", "paused", "incomplete", "incomplete_expired"}:
        account.access_state = "canceled"

    await _apply_account_access_state(db, account)


@router.get("/checkout/{plan}")
async def checkout(plan: str):
    if plan == "enterprise":
        subject = "Enterprise%20Plan%20Inquiry"
        return RedirectResponse(
            f"mailto:{ENTERPRISE_EMAIL}?subject={subject}",
            status_code=303,
        )

    if plan not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    stripe.api_key = _load_stripe_key()
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    p = PLANS[plan]
    base_url = os.getenv("BASE_URL", "https://www.agentlens.one")

    try:
        checkout_kwargs = {
            "mode": "subscription",
            "line_items": [{
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": p["name"],
                        "description": p["description"],
                    },
                    "unit_amount": p["amount"],
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            "success_url": f"{base_url}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}/",
            "allow_promotion_codes": True,
            "payment_method_types": _payment_method_types(),
            "custom_text": {
                "submit": {
                    "message": f"By subscribing, you agree to a {CONTRACT_TERM_MONTHS}-month contract term with monthly billing."
                }
            },
            "metadata": {
                "plan": plan,
                "source": "website_checkout",
                "contract_term_months": str(CONTRACT_TERM_MONTHS),
                "billing_interval": "month",
            },
            "subscription_data": {
                "metadata": {
                    "plan": plan,
                    "contract_term_months": str(CONTRACT_TERM_MONTHS),
                    "billing_interval": "month",
                }
            },
        }
        session = await asyncio.to_thread(
            lambda: stripe.checkout.Session.create(**checkout_kwargs)
        )
    except stripe.StripeError as e:
        # Resilient fallback: if SEPA is not yet activated in Stripe, keep checkout
        # operational with card-only instead of returning a hard error to users.
        err_text = (getattr(e, "user_message", "") or str(e) or "").lower()
        configured_methods = checkout_kwargs.get("payment_method_types", [])
        if "sepa_debit" in configured_methods and (
            "sepa_debit" in err_text or "payment method type provided" in err_text
        ):
            checkout_kwargs["payment_method_types"] = ["card"]
            try:
                session = await asyncio.to_thread(
                    lambda: stripe.checkout.Session.create(**checkout_kwargs)
                )
            except stripe.StripeError as inner:
                raise HTTPException(status_code=502, detail=f"Stripe error: {inner.user_message}")
        else:
            raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message}")

    return RedirectResponse(session.url, status_code=303)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    stripe.api_key = _load_stripe_key()
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    webhook_secret = _load_stripe_webhook_secret()
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured. Set STRIPE_WEBHOOK_SECRET.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("mode") == "subscription":
            customer_details = session.get("customer_details") or {}
            amount_total = session.get("amount_total")
            notify_payload = {
                "event_kind": "billing_checkout_completed",
                "event_id": event.get("id"),
                "timestamp": time.time(),
                "plan": (session.get("metadata") or {}).get("plan", "unknown"),
                "source": (session.get("metadata") or {}).get("source", "unknown"),
                "contract_term_months": (session.get("metadata") or {}).get("contract_term_months", str(CONTRACT_TERM_MONTHS)),
                "billing_interval": (session.get("metadata") or {}).get("billing_interval", "month"),
                "email": customer_details.get("email") or session.get("customer_email"),
                "name": customer_details.get("name"),
                "amount_total": (amount_total / 100) if isinstance(amount_total, int) else amount_total,
                "currency": (session.get("currency") or "").upper(),
                "customer_id": session.get("customer"),
                "subscription_id": session.get("subscription"),
                "checkout_session_id": session.get("id"),
                "payment_status": session.get("payment_status"),
            }
            await _notify_billing_event(notify_payload)
            await _sync_checkout_completed_to_account(db, session)

    if event.get("type") == "customer.subscription.updated":
        sub = event["data"]["object"] or {}
        await _sync_subscription_status_to_account(
            db,
            customer_id=sub.get("customer"),
            subscription_id=sub.get("id"),
            subscription_status=sub.get("status", ""),
        )

    if event.get("type") == "customer.subscription.deleted":
        sub = event["data"]["object"] or {}
        await _sync_subscription_status_to_account(
            db,
            customer_id=sub.get("customer"),
            subscription_id=sub.get("id"),
            subscription_status="canceled",
        )

    if event.get("type") == "invoice.payment_failed":
        inv = event["data"]["object"] or {}
        await _sync_subscription_status_to_account(
            db,
            customer_id=inv.get("customer"),
            subscription_id=inv.get("subscription"),
            subscription_status="past_due",
        )

    if event.get("type") == "invoice.paid":
        inv = event["data"]["object"] or {}
        await _sync_subscription_status_to_account(
            db,
            customer_id=inv.get("customer"),
            subscription_id=inv.get("subscription"),
            subscription_status="active",
        )

    await db.commit()

    return {"received": True}


@router.post("/onboarding-intake")
async def onboarding_intake(request: Request):
    stripe.api_key = _load_stripe_key()
    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    try:
        form_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    session_id = _clean_text(form_data.get("session_id"), 255)
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    try:
        session = await asyncio.to_thread(
            lambda: stripe.checkout.Session.retrieve(session_id)
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message or str(e)}")

    if (session.get("mode") or "") != "subscription":
        raise HTTPException(status_code=400, detail="Session is not a subscription checkout")

    customer_details = session.get("customer_details") or {}
    amount_total = session.get("amount_total")
    intake_payload = {
        "event_kind": "billing_onboarding_submitted",
        "timestamp": time.time(),
        "plan": (session.get("metadata") or {}).get("plan", "unknown"),
        "contract_term_months": (session.get("metadata") or {}).get("contract_term_months", str(CONTRACT_TERM_MONTHS)),
        "billing_interval": (session.get("metadata") or {}).get("billing_interval", "month"),
        "email": customer_details.get("email") or session.get("customer_email"),
        "name": customer_details.get("name"),
        "amount_total": (amount_total / 100) if isinstance(amount_total, int) else amount_total,
        "currency": (session.get("currency") or "").upper(),
        "customer_id": session.get("customer"),
        "subscription_id": session.get("subscription"),
        "checkout_session_id": session.get("id"),
        "payment_status": session.get("payment_status"),
        "company_name": _clean_text(form_data.get("company_name"), 160),
        "company_website": _clean_text(form_data.get("company_website"), 300),
        "use_case": _clean_text(form_data.get("use_case"), 1500),
        "team_size": _clean_text(form_data.get("team_size"), 80),
        "monthly_volume": _clean_text(form_data.get("monthly_volume"), 120),
        "technical_contact_name": _clean_text(form_data.get("technical_contact_name"), 160),
        "technical_contact_email": _clean_text(form_data.get("technical_contact_email"), 320),
        "kickoff_timeline": _clean_text(form_data.get("kickoff_timeline"), 120),
        "implementation_notes": _clean_text(form_data.get("implementation_notes"), 2000),
    }

    await _notify_billing_event(intake_payload)
    return {"received": True}
