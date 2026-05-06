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
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

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


async def _notify_billing_event(payload: dict[str, Any]) -> None:
    webhook_url = os.environ.get("BILLING_EVENT_WEBHOOK_URL", "").strip()
    resend_api_key = os.environ.get("RESEND_API_KEY", "").strip()
    notify_email = os.environ.get("BILLING_NOTIFY_EMAIL", "").strip()
    from_email = os.environ.get("BILLING_NOTIFY_FROM_EMAIL", "AgentLens Billing <noreply@agentlens.one>").strip()

    async with httpx.AsyncClient(timeout=10) as client:
        if webhook_url:
            try:
                await client.post(
                    webhook_url,
                    json={
                        "event": "billing_checkout_completed",
                        "timestamp": payload.get("timestamp", time.time()),
                        "billing": payload,
                    },
                )
            except Exception:
                pass

        if resend_api_key and notify_email:
            try:
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
async def stripe_webhook(request: Request):
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

    return {"received": True}
