import os
import random
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import SessionFactory, get_session
from storage.models import ApiKey, Evaluation, Request, Span, Trace

router = APIRouter(prefix="/admin")

DEMO_KEY = "al_demo_agentlens"


def _require_admin(token: str | None):
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token or token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


class CreateKeyPayload(BaseModel):
    label: str
    plan: str = "pilot"


@router.post("/api-keys")
async def create_api_key(
    payload: CreateKeyPayload,
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    key = "al_" + secrets.token_urlsafe(24)
    obj = ApiKey(key=key, label=payload.label, plan=payload.plan, created_at=time.time())
    db.add(obj)
    await db.commit()
    return {"key": key, "label": payload.label, "plan": payload.plan}


@router.get("/api-keys")
async def list_api_keys(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        {"key": k.key, "label": k.label, "plan": k.plan, "active": k.active, "created_at": k.created_at}
        for k in keys
    ]


@router.delete("/api-keys/{key}")
async def deactivate_api_key(
    key: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Key not found")
    obj.active = False
    await db.commit()
    return {"deactivated": key}


async def _do_seed_demo(db: AsyncSession) -> dict:
    """Insert demo API key + realistic data. Idempotent — safe to call on every startup."""

    # Always upsert demo key with active=1 via raw SQL (bypasses ORM default quirks)
    await db.execute(text(
        "INSERT OR REPLACE INTO api_keys (key, label, plan, created_at, active) "
        "VALUES (:key, 'Live Demo', 'demo', :ts, 1)"
    ), {"key": DEMO_KEY, "ts": time.time()})

    now = time.time()

    # If demo data exists, keep it and only top up recent (last 24h) data if needed.
    count = (await db.execute(
        select(func.count()).select_from(Request).where(Request.api_key == DEMO_KEY)
    )).scalar()
    if count > 0:
        recent_24h = (await db.execute(
            select(func.count()).select_from(Request).where(
                Request.api_key == DEMO_KEY,
                Request.timestamp >= now - 24 * 3600,
            )
        )).scalar() or 0

        if recent_24h < 12:
            inserted = await _top_up_recent_demo_data(db, now=now, count=int(12 - recent_24h))
            await db.commit()
            return {
                "key": DEMO_KEY,
                "status": "topup_seeded",
                "requests_total": int(count) + inserted,
                "recent_24h": int(recent_24h) + inserted,
                "inserted": inserted,
            }

        await db.commit()
        return {"key": DEMO_KEY, "status": "already_seeded", "requests": count, "recent_24h": int(recent_24h)}

    SCENARIOS = [
        {"prompt": "Answer the user's question accurately and concisely.", "input": "What is the capital of France?", "output": "The capital of France is Paris. It has been the country's capital since the 10th century and is home to about 2.1 million people in the city proper.", "model": "gpt-4o", "cost_usd": 0.0012, "hours_ago": 1, "quality": 0.95, "hallucination": 0.02, "flags": [], "explanation": "Accurate, concise, no hallucinations.", "feature": "qa"},
        {"prompt": "Summarize the following text in 2-3 sentences.", "input": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.", "output": "Machine learning is an AI subfield where systems improve through experience without explicit programming. It uses algorithms to find patterns in data and make decisions. Applications range from recommendation systems to medical diagnosis.", "model": "gpt-4o", "cost_usd": 0.0018, "hours_ago": 2, "quality": 0.91, "hallucination": 0.05, "flags": [], "explanation": "Clear, accurate summary within the requested length.", "feature": "summarize"},
        {"prompt": "Write a professional email response.", "input": "Customer complaint about delayed shipment", "output": "Dear valued customer, I sincerely apologize for the delay in your shipment. We have investigated the issue and found it was caused by an unexpected logistics disruption. Your order is now prioritized and will arrive within 2 business days. As compensation, we are offering a 15% discount on your next order.", "model": "claude-3-haiku", "cost_usd": 0.0008, "hours_ago": 3, "quality": 0.93, "hallucination": 0.03, "flags": [], "explanation": "Professional tone, clear apology, actionable resolution.", "feature": "email"},
        {"prompt": "Generate a SQL query for the following request.", "input": "Get all users who signed up in the last 30 days", "output": "SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '30 days' ORDER BY created_at DESC;", "model": "gpt-4o", "cost_usd": 0.0015, "hours_ago": 4, "quality": 0.96, "hallucination": 0.01, "flags": [], "explanation": "Syntactically correct, uses standard SQL.", "feature": "sql"},
        {"prompt": "Debug this Python code and explain the error.", "input": "def add(a, b): return a + b\nresult = add('5', 3)", "output": "The error is a TypeError: can only concatenate str (not 'int') to str. Fix: convert the string to int first: result = add(int('5'), 3).", "model": "gpt-4o", "cost_usd": 0.002, "hours_ago": 5, "quality": 0.94, "hallucination": 0.02, "flags": [], "explanation": "Correct diagnosis and fix.", "feature": "code"},
        {"prompt": "Classify the sentiment of this review.", "input": "This product exceeded all my expectations. Absolutely love it!", "output": "Sentiment: Positive (confidence: 0.98). The review expresses strong satisfaction with superlatives indicating very high customer approval.", "model": "claude-3-haiku", "cost_usd": 0.0006, "hours_ago": 6, "quality": 0.92, "hallucination": 0.03, "flags": [], "explanation": "Correct sentiment, appropriate confidence.", "feature": "sentiment"},
        {"prompt": "Translate to German.", "input": "The meeting is scheduled for Monday at 3pm.", "output": "Das Meeting ist für Montag um 15 Uhr geplant.", "model": "gpt-4o", "cost_usd": 0.001, "hours_ago": 7, "quality": 0.97, "hallucination": 0.01, "flags": [], "explanation": "Accurate translation.", "feature": "translate"},
        {"prompt": "Write a detailed product description for an e-commerce listing.", "input": "Wireless bluetooth headphones with noise cancellation", "output": "These are wireless headphones. They have bluetooth and noise cancellation. Good for music.", "model": "gpt-4o-mini", "cost_usd": 0.0003, "hours_ago": 8, "quality": 0.42, "hallucination": 0.10, "flags": ["low_detail"], "explanation": "Response is far too brief given the request for a detailed description.", "feature": "copywriting"},
        {"prompt": "Analyze the root causes of this customer churn.", "input": "Customer canceled after 3 months, cited 'too expensive' and 'missing features'", "output": "The customer left because of price and features. This is common. You should consider pricing changes.", "model": "claude-3-haiku", "cost_usd": 0.0005, "hours_ago": 10, "quality": 0.38, "hallucination": 0.08, "flags": ["low_detail"], "explanation": "Superficial analysis with no actionable insights.", "feature": "analysis"},
        {"prompt": "Generate creative marketing copy for social media.", "input": "New coffee brand targeting millennials", "output": "Try our coffee. It tastes good. Buy now.", "model": "gpt-4o-mini", "cost_usd": 0.0002, "hours_ago": 12, "quality": 0.35, "hallucination": 0.05, "flags": ["low_quality"], "explanation": "Generic, uninspired copy with no brand voice.", "feature": "marketing"},
        {"prompt": "Summarize quantum computing in one sentence.", "input": "Explain quantum computing briefly", "output": "ok", "model": "claude-3-haiku", "cost_usd": 0.0002, "hours_ago": 14, "quality": 0.05, "hallucination": 0.0, "flags": ["empty_response"], "explanation": "Response contains no useful information.", "feature": "summarize"},
        {"prompt": "Write a haiku about technology.", "input": "Haiku about AI", "output": "Technology is good. Computers help us every day. The future is bright. Technology is good. Computers help us every day. The future is bright.", "model": "gpt-4o-mini", "cost_usd": 0.0003, "hours_ago": 16, "quality": 0.12, "hallucination": 0.15, "flags": ["repetition"], "explanation": "Response contains exact repetition — likely a generation error.", "feature": "creative"},
        {"prompt": "Extract all action items from this meeting transcript.", "input": "John will follow up on the budget. Sarah needs to prepare the Q3 report by Friday. Team to review the new design mockups.", "output": "There were some action items mentioned in the meeting.", "model": "claude-3-haiku", "cost_usd": 0.0004, "hours_ago": 18, "quality": 0.08, "hallucination": 0.0, "flags": ["empty_response"], "explanation": "Failed to extract any of the three action items.", "feature": "extraction"},
        {"prompt": "Provide a data-driven market analysis.", "input": "Analyze the EV market in 2024", "output": "According to recent studies, the EV market is the best investment opportunity. Scientists say EVs will always dominate. The only way to succeed is to invest in EVs immediately.", "model": "gpt-4o", "cost_usd": 0.0014, "hours_ago": 20, "quality": 0.15, "hallucination": 0.85, "flags": ["hallucination", "overconfident"], "explanation": "Multiple unverified absolute claims. High hallucination risk.", "feature": "analysis"},
        {"prompt": "Answer the user's coding question with a working example.", "input": "How do I center a div in CSS?", "output": "", "model": "gpt-4o-mini", "cost_usd": 0.0001, "hours_ago": 22, "quality": 0.0, "hallucination": 0.0, "flags": ["empty_response"], "explanation": "Empty response — model returned nothing.", "feature": "code"},
    ]

    for s in SCENARIOS:
        req_id = str(uuid.uuid4())
        ts = now - s["hours_ago"] * 3600
        db.add(Request(id=req_id, api_key=DEMO_KEY, input=s["input"], output=s["output"], prompt=s["prompt"], model=s["model"], metadata_={"feature": s["feature"], "cost_usd": s["cost_usd"], "input_tokens": max(1, len(s["input"]) // 4), "output_tokens": max(1, len(s["output"]) // 4)}, timestamp=ts))
        db.add(Evaluation(request_id=req_id, quality_score=s["quality"], hallucination_score=s["hallucination"], flags=s["flags"], score_explanation=s["explanation"]))

    t1_id = str(uuid.uuid4())
    t1_start = now - 2 * 3600
    db.add(Trace(id=t1_id, api_key=DEMO_KEY, name="customer_support_agent", status="completed", input="User: My order #4521 hasn't arrived and it's been 10 days.", output="Resolved: Order located, expedited reshipment initiated, 20% discount applied.", total_tokens=1840, total_cost_usd=0.0138, total_duration_ms=4200, started_at=t1_start, ended_at=t1_start + 4.2))
    for sp in [
        {"name": "classify_intent", "type": "llm", "model": "gpt-4o-mini", "tokens": 210, "cost": 0.0001, "dur": 380, "offset": 0.0, "input": "User: My order #4521 hasn't arrived.", "output": "intent: ORDER_STATUS, urgency: HIGH", "status": "completed", "error": None},
        {"name": "lookup_order", "type": "tool", "model": None, "tokens": None, "cost": None, "dur": 120, "offset": 0.4, "input": "order_id: 4521", "output": '{"status": "delayed", "carrier": "DHL"}', "status": "completed", "error": None},
        {"name": "generate_response", "type": "llm", "model": "gpt-4o", "tokens": 980, "cost": 0.0073, "dur": 1800, "offset": 0.6, "input": "Order delayed. Generate empathetic resolution.", "output": "I sincerely apologize for the delay...", "status": "completed", "error": None},
        {"name": "apply_compensation", "type": "tool", "model": None, "tokens": None, "cost": None, "dur": 90, "offset": 2.5, "input": "discount: 20%, order_id: 4521", "output": '{"applied": true, "code": "SORRY20"}', "status": "completed", "error": None},
    ]:
        db.add(Span(id=str(uuid.uuid4()), trace_id=t1_id, name=sp["name"], span_type=sp["type"], status=sp["status"], input=sp["input"], output=sp["output"], model=sp.get("model"), tokens=sp.get("tokens"), cost_usd=sp.get("cost"), duration_ms=sp["dur"], error=sp.get("error"), started_at=t1_start + sp["offset"], ended_at=t1_start + sp["offset"] + sp["dur"] / 1000))

    t2_id = str(uuid.uuid4())
    t2_start = now - 5 * 3600
    db.add(Trace(id=t2_id, api_key=DEMO_KEY, name="market_research_agent", status="failed", input="Analyze Q1 2024 EV market trends for investor report.", output=None, total_tokens=2100, total_cost_usd=0.0158, total_duration_ms=8500, error="External data source timeout after 3 retries", started_at=t2_start, ended_at=t2_start + 8.5))
    for sp in [
        {"name": "decompose_query", "type": "llm", "model": "gpt-4o", "tokens": 320, "cost": 0.0024, "dur": 650, "offset": 0.0, "input": "Analyze Q1 2024 EV market trends", "output": "Sub-tasks: [1. Sales data, 2. Policy changes]", "status": "completed", "error": None},
        {"name": "fetch_sales_data", "type": "retrieval", "model": None, "tokens": None, "cost": None, "dur": 3200, "offset": 0.7, "input": "source: ev_market_db, quarter: Q1_2024", "output": None, "status": "failed", "error": "Connection timeout after 3 retries"},
        {"name": "fetch_policy_news", "type": "retrieval", "model": None, "tokens": None, "cost": None, "dur": 890, "offset": 0.7, "input": "search: EV policy Europe Q1 2024", "output": "Found 12 relevant articles on EU EV mandates.", "status": "completed", "error": None},
        {"name": "synthesize_partial", "type": "llm", "model": "gpt-4o", "tokens": 1780, "cost": 0.0134, "dur": 2100, "offset": 4.5, "input": "Partial data only. Synthesize with caveat.", "output": "Note: Sales data unavailable. Policy analysis only...", "status": "completed", "error": None},
    ]:
        db.add(Span(id=str(uuid.uuid4()), trace_id=t2_id, name=sp["name"], span_type=sp["type"], status=sp["status"], input=sp.get("input"), output=sp.get("output"), model=sp.get("model"), tokens=sp.get("tokens"), cost_usd=sp.get("cost"), duration_ms=sp["dur"], error=sp.get("error"), started_at=t2_start + sp["offset"], ended_at=t2_start + sp["offset"] + sp["dur"] / 1000))

    await db.commit()
    return {"key": DEMO_KEY, "status": "seeded", "requests": len(SCENARIOS), "traces": 2}


async def _top_up_recent_demo_data(db: AsyncSession, *, now: float, count: int) -> int:
    if count <= 0:
        return 0

    samples = [
        {
            "prompt": "Answer the user's question accurately and concisely.",
            "input": "How do I center a div in CSS?",
            "output": "Use a parent with display:flex; justify-content:center; align-items:center; and define parent height.",
            "model": "gpt-4o",
            "cost_usd": 0.0011,
            "quality": 0.94,
            "hallucination": 0.02,
            "flags": [],
            "explanation": "Accurate and directly actionable answer.",
            "feature": "code",
        },
        {
            "prompt": "Summarize this user request in one sentence.",
            "input": "Need a German summary of GDPR retention requirements.",
            "output": "Der Nutzer mÃ¶chte eine kurze, klare Zusammenfassung von DSGVO-Aufbewahrungsregeln.",
            "model": "claude-3-haiku",
            "cost_usd": 0.0005,
            "quality": 0.91,
            "hallucination": 0.03,
            "flags": [],
            "explanation": "Good one-line summary.",
            "feature": "summarize",
        },
        {
            "prompt": "Answer with concrete next steps.",
            "input": "Why did support ticket triage fail?",
            "output": "ok",
            "model": "gpt-4o-mini",
            "cost_usd": 0.0002,
            "quality": 0.06,
            "hallucination": 0.0,
            "flags": ["empty_response"],
            "explanation": "Response does not answer the question.",
            "feature": "support",
        },
    ]

    inserted = 0
    for i in range(count):
        s = samples[i % len(samples)]
        ts = now - random.uniform(5 * 60, 20 * 3600)
        req_id = str(uuid.uuid4())
        db.add(
            Request(
                id=req_id,
                api_key=DEMO_KEY,
                input=s["input"],
                output=s["output"],
                prompt=s["prompt"],
                model=s["model"],
                metadata_={
                    "feature": s["feature"],
                    "cost_usd": s["cost_usd"],
                    "input_tokens": max(1, len(s["input"]) // 4),
                    "output_tokens": max(1, len(s["output"]) // 4),
                },
                timestamp=ts,
            )
        )
        db.add(
            Evaluation(
                request_id=req_id,
                quality_score=s["quality"],
                hallucination_score=s["hallucination"],
                flags=s["flags"],
                score_explanation=s["explanation"],
            )
        )
        inserted += 1
    return inserted


async def seed_demo_on_startup() -> None:
    """Auto-called on every server start — demo data is always present."""
    async with SessionFactory() as db:
        await _do_seed_demo(db)


@router.post("/seed-demo")
async def seed_demo(
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger demo seeding. Idempotent."""
    _require_admin(token)
    return await _do_seed_demo(db)
