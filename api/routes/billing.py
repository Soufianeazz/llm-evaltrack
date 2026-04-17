"""
Stripe billing — checkout sessions for Starter, Team, and Scale plans.
Enterprise redirects to sales contact.
"""
import asyncio
import os
import stripe
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/billing")

stripe.api_key = (os.getenv("STRIPE_SECRET_KEY") or os.getenv("stripe_secret_key", "")).strip()

PLANS = {
    "starter": {
        "name": "AgentLens Starter",
        "description": "Managed hosting, up to 1M calls/month, 1 project, email support, onboarding call",
        "amount": 29900,  # €299/month
    },
    "team": {
        "name": "AgentLens Team",
        "description": "Up to 10M calls/month, 5 projects, GDPR DPA included, Slack support, monthly review call",
        "amount": 99900,  # €999/month
    },
    "scale": {
        "name": "AgentLens Scale",
        "description": "Up to 50M calls/month, unlimited projects, dedicated cloud instance, 99.9% SLA, security package",
        "amount": 299900,  # €2,999/month
    },
}

ENTERPRISE_EMAIL = "contact@agentlens.io"


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

    if not stripe.api_key:
        raise HTTPException(status_code=503, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")

    p = PLANS[plan]
    base_url = os.getenv("BASE_URL", "https://llm-evaltrack-production.up.railway.app")

    try:
        session = await asyncio.to_thread(
            lambda: stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{
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
                success_url=f"{base_url}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/landing.html",
                allow_promotion_codes=True,
            )
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message}")

    return RedirectResponse(session.url, status_code=303)
