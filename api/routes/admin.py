import random
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_auth import require_admin_token
from storage.database import SessionFactory, get_session
from storage.models import ApiKey, AuditLog, Evaluation, Request, SelfHostInstance, Span, Trace

router = APIRouter(prefix="/admin")

DEMO_KEY = "al_demo_agentlens"


class CreateKeyPayload(BaseModel):
    label: str
    plan: str = "pilot"
    role: str = "admin"
    expires_at: float | None = None
    trial_days: int | None = None


class SetRolePayload(BaseModel):
    role: str


class SetExpiryPayload(BaseModel):
    expires_at: float | None = None
    trial_days: int | None = None


def _mask_key(key: str) -> str:
    if len(key) < 8:
        return key
    return f"{key[:6]}...{key[-4:]}"


async def _audit(db: AsyncSession, action: str, detail: str) -> None:
    db.add(AuditLog(id=str(uuid.uuid4()), action=action, detail=detail, timestamp=time.time()))
    await db.commit()


def resolve_key_expiry(
    *,
    plan: str,
    trial_days: int | None,
    expires_at: float | None,
    now: float | None = None,
) -> float | None:
    if expires_at is not None:
        return expires_at
    if trial_days is not None:
        if trial_days <= 0:
            raise ValueError("trial_days must be greater than zero")
        return (time.time() if now is None else now) + trial_days * 24 * 60 * 60
    if plan in {"pilot", "pilot14", "pilot_14", "full_pilot"}:
        return (time.time() if now is None else now) + 14 * 24 * 60 * 60
    return None


@router.post("/api-keys")
async def create_api_key(
    payload: CreateKeyPayload,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    if payload.role not in {"admin", "analyst", "read_only"}:
        raise HTTPException(status_code=422, detail="Invalid role. Use admin, analyst, or read_only.")
    key = "al_" + secrets.token_urlsafe(24)
    now = time.time()
    try:
        expires_at = resolve_key_expiry(
            plan=payload.plan,
            trial_days=payload.trial_days,
            expires_at=payload.expires_at,
            now=now,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    obj = ApiKey(
        key=key,
        label=payload.label,
        plan=payload.plan,
        role=payload.role,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(obj)
    await db.commit()
    await _audit(
        db,
        "api_key_created",
        f"key={_mask_key(key)} plan={payload.plan} role={payload.role} expires_at={expires_at} label={payload.label}",
    )
    return {"key": key, "label": payload.label, "plan": payload.plan, "role": payload.role, "expires_at": expires_at}


@router.get("/api-keys")
async def list_api_keys(
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        {
            "key": k.key,
            "label": k.label,
            "plan": k.plan,
            "role": k.role or "admin",
            "active": k.active,
            "created_at": k.created_at,
            "expires_at": getattr(k, "expires_at", None),
        }
        for k in keys
    ]


@router.delete("/api-keys/{key}")
async def deactivate_api_key(
    key: str,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Key not found")
    obj.active = False
    await db.commit()
    await _audit(db, "api_key_deactivated", f"key={_mask_key(key)} reason=manual")
    return {"deactivated": key}


@router.post("/api-keys/{key}/role")
async def set_api_key_role(
    key: str,
    payload: SetRolePayload,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    if payload.role not in {"admin", "analyst", "read_only"}:
        raise HTTPException(status_code=422, detail="Invalid role. Use admin, analyst, or read_only.")
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Key not found")
    obj.role = payload.role
    await db.commit()
    await _audit(db, "api_key_role_changed", f"key={_mask_key(key)} role={payload.role}")
    return {"key": key, "role": payload.role}


@router.post("/api-keys/{key}/expiry")
async def set_api_key_expiry(
    key: str,
    payload: SetExpiryPayload,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Key not found")
    try:
        expires_at = resolve_key_expiry(
            plan=obj.plan or "pilot",
            trial_days=payload.trial_days,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    obj.expires_at = expires_at
    if expires_at is None:
        await _audit(db, "api_key_expiry_cleared", f"key={_mask_key(key)}")
    else:
        await _audit(db, "api_key_expiry_set", f"key={_mask_key(key)} expires_at={expires_at}")
    await db.commit()
    return {"key": _mask_key(key), "expires_at": expires_at}


@router.post("/api-keys/{key}/rotate")
async def rotate_api_key(
    key: str,
    grace_hours: int = Query(24, ge=0, le=168),
    reason: str = Query("scheduled", pattern="^(scheduled|emergency|manual)$"),
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(ApiKey).where(ApiKey.key == key))
    old_key = result.scalar_one_or_none()
    if not old_key:
        raise HTTPException(status_code=404, detail="Key not found")
    if not old_key.active:
        raise HTTPException(status_code=409, detail="Key already inactive")

    rotation_id = f"rot_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    await _audit(
        db,
        "api_key_rotation_started",
        (
            f"rotation_id={rotation_id} old_key={_mask_key(old_key.key)} "
            f"reason={reason} grace_hours={grace_hours}"
        ),
    )

    new_key = "al_" + secrets.token_urlsafe(24)
    new_obj = ApiKey(
        key=new_key,
        label=old_key.label,
        plan=old_key.plan,
        role=old_key.role or "admin",
        created_at=time.time(),
        expires_at=getattr(old_key, "expires_at", None),
        active=True,
    )
    db.add(new_obj)
    await db.commit()
    await _audit(
        db,
        "api_key_created",
        f"rotation_id={rotation_id} key={_mask_key(new_key)} plan={old_key.plan}",
    )

    if reason == "emergency" or grace_hours == 0:
        old_key.active = False
        await db.commit()
        await _audit(
            db,
            "api_key_deactivated",
            f"rotation_id={rotation_id} key={_mask_key(old_key.key)} reason={reason}",
        )
        await _audit(db, "api_key_rotation_completed", f"rotation_id={rotation_id} mode=immediate")
        return {
            "rotation_id": rotation_id,
            "mode": "immediate",
            "old_key_deactivated": True,
            "new_key": new_key,
            "grace_hours": 0,
        }

    await _audit(
        db,
        "api_key_rotation_grace_started",
        f"rotation_id={rotation_id} old_key={_mask_key(old_key.key)} grace_hours={grace_hours}",
    )
    return {
        "rotation_id": rotation_id,
        "mode": "grace",
        "old_key_deactivated": False,
        "new_key": new_key,
        "grace_hours": grace_hours,
    }


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
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger demo seeding. Idempotent."""
    result = await _do_seed_demo(db)
    await _audit(db, "admin_seed_demo", f"status={result.get('status')} requests={result.get('requests', result.get('requests_total'))}")
    return result


@router.post("/pilot-pulse")
async def pilot_pulse(
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    """
    Pings opt-in healthcheck URLs of registered pilot self-host instances.
    Updates `last_pinged_at` on success. Returns a per-instance report.

    Read-only on the customer side (HTTP GET). Only instances that explicitly
    opted in by setting `healthcheck_url` are touched.
    """
    import asyncio
    import httpx as _httpx

    result = await db.execute(
        select(SelfHostInstance).where(
            SelfHostInstance.pilot == True,  # noqa: E712 — SQLAlchemy comparison
            SelfHostInstance.healthcheck_url.isnot(None),
        )
    )
    instances = result.scalars().all()

    if not instances:
        return {"checked": 0, "results": []}

    async def _probe(client: _httpx.AsyncClient, inst: SelfHostInstance) -> dict:
        url = inst.healthcheck_url
        out: dict[str, object] = {
            "instance_id": inst.id,
            "label": inst.label,
            "url": url,
        }
        try:
            r = await client.get(url, timeout=8)
            out["ok"] = 200 <= r.status_code < 300
            out["status"] = r.status_code
        except Exception as exc:  # noqa: BLE001
            out["ok"] = False
            out["status"] = None
            out["error"] = f"{type(exc).__name__}: {str(exc)[:100]}"
        return out

    async with _httpx.AsyncClient(follow_redirects=True) as client:
        results = await asyncio.gather(*[_probe(client, i) for i in instances])

    now = time.time()
    for inst, res in zip(instances, results):
        if res.get("ok"):
            inst.last_pinged_at = now
    await db.commit()
    await _audit(
        db,
        "admin_pilot_pulse",
        f"checked={len(results)} healthy={sum(1 for r in results if r.get('ok'))}",
    )
    return {"checked": len(results), "results": results, "timestamp": now}


@router.post("/backup/snapshot")
async def backup_snapshot(
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    """
    Returns a clean SQLite snapshot of the live database.

    Uses the SQLite Backup API (`connection.backup`) which produces a consistent
    copy even while writes are in flight — safer than `cp` of a hot DB file.

    Read-only on the source DB. Available to:
      - Our Railway production for weekly off-site backups (volume-backup-runner agent).
      - Self-host customers (Bibin) who want their own backups via their admin token.
    """
    import asyncio
    import shutil
    import sqlite3
    import tempfile
    import time as _time
    from pathlib import Path

    from fastapi import HTTPException
    from sqlalchemy.engine.url import make_url
    from starlette.background import BackgroundTask
    from starlette.responses import FileResponse

    from storage.database import DATABASE_URL

    # Only support SQLite — other backends would need a different mechanism.
    if "sqlite" not in DATABASE_URL.lower():
        raise HTTPException(status_code=400, detail="Backup endpoint only supports SQLite databases.")

    try:
        url = make_url(DATABASE_URL)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Cannot parse DATABASE_URL: {exc}") from exc

    db_path_str = url.database or ""
    # Resolve relative paths against current working directory (which the API runs in).
    db_path = Path(db_path_str)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    if not db_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file not found at expected path: {db_path}",
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="agentlens-backup-"))
    ts = _time.strftime("%Y%m%dT%H%M%SZ", _time.gmtime())
    snap_path = tmp_dir / f"agentlens-{ts}.db"

    def _do_backup() -> None:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(snap_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    try:
        await asyncio.to_thread(_do_backup)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Backup failed: {exc}") from exc

    # Audit AFTER backup succeeds — failed backups should not leave a misleading log.
    size_bytes = snap_path.stat().st_size
    await _audit(db, "admin_backup_snapshot", f"size_bytes={size_bytes} file={snap_path.name}")

    return FileResponse(
        str(snap_path),
        media_type="application/octet-stream",
        filename=snap_path.name,
        background=BackgroundTask(shutil.rmtree, str(tmp_dir), ignore_errors=True),
    )
