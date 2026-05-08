"""
Agent debugging endpoints — traces and spans for multi-step agent runs.
"""
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from api.admin_auth import require_admin_token
from api.auth import ApiKeyContext, ensure_role, require_api_key_context
from api.costing import compute_cost_from_tokens
from api.limiter import limiter
from api.plan_access import PlanContext, require_feature
from storage.database import get_session
from storage.models import AuditLog, Span, Trace

router = APIRouter(prefix="/traces")


def _span_effective_cost(span: Span) -> float:
    # Prefer explicit span token split when available.
    meta = span.metadata_ or {}
    in_tokens = meta.get("input_tokens")
    out_tokens = meta.get("output_tokens")
    try:
        if in_tokens is not None and out_tokens is not None:
            computed = compute_cost_from_tokens(
                span.model,
                int(float(in_tokens)),
                int(float(out_tokens)),
            )
            if computed is not None:
                return computed
    except Exception:
        pass

    # Fallback: estimate split from total tokens if available.
    try:
        if span.tokens is not None:
            total = max(0, int(float(span.tokens)))
            # Conservative approximation when split is missing.
            est_input = int(total * 0.6)
            est_output = max(0, total - est_input)
            computed = compute_cost_from_tokens(span.model, est_input, est_output)
            if computed is not None:
                return computed
    except Exception:
        pass

    return float(span.cost_usd or 0.0)


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateTracePayload(BaseModel):
    name: str = Field(..., min_length=1)
    input: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndTracePayload(BaseModel):
    status: str = Field("completed", pattern="^(completed|failed)$")
    output: str | None = None
    error: str | None = None


class CreateSpanPayload(BaseModel):
    name: str = Field(..., min_length=1)
    span_type: str = Field("custom", pattern="^(llm|tool|retrieval|decision|custom)$")
    parent_span_id: str | None = None
    input: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndSpanPayload(BaseModel):
    status: str = Field("completed", pattern="^(completed|failed)$")
    output: str | None = None
    error: str | None = None
    tokens: float | None = None
    cost_usd: float | None = None


# ── Trace CRUD ────────────────────────────────────────────────────────────────

@router.post("")
@limiter.limit("60/minute")
async def create_trace(
    request: Request,
    payload: CreateTracePayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    ensure_role(ctx, "admin", "analyst")
    trace_id = str(uuid.uuid4())
    trace = Trace(
        id=trace_id,
        api_key=plan_ctx.key,
        name=payload.name,
        input=payload.input,
        status="running",
        metadata_=payload.metadata,
        started_at=time.time(),
    )
    db.add(trace)
    await db.commit()
    return {"trace_id": trace_id}


@router.post("/{trace_id}/end")
@limiter.limit("120/minute")
async def end_trace(
    request: Request,
    trace_id: str,
    payload: EndTracePayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    ensure_role(ctx, "admin", "analyst")
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.api_key == plan_ctx.key))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    now = time.time()
    trace.status = payload.status
    trace.output = payload.output
    trace.error = payload.error
    trace.ended_at = now
    trace.total_duration_ms = round((now - trace.started_at) * 1000, 1)

    spans_result = await db.execute(select(Span).where(Span.trace_id == trace_id))
    spans = spans_result.scalars().all()
    trace.total_tokens = sum(s.tokens or 0 for s in spans)
    trace.total_cost_usd = sum(_span_effective_cost(s) for s in spans)

    await db.commit()
    return {"trace_id": trace_id, "status": trace.status, "duration_ms": trace.total_duration_ms}


# ── Span CRUD ─────────────────────────────────────────────────────────────────

@router.post("/{trace_id}/spans")
@limiter.limit("300/minute")
async def create_span(
    request: Request,
    trace_id: str,
    payload: CreateSpanPayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    ensure_role(ctx, "admin", "analyst")
    # Verify trace belongs to this api_key
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.api_key == plan_ctx.key))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="trace not found")

    span_id = str(uuid.uuid4())
    span = Span(
        id=span_id,
        trace_id=trace_id,
        parent_span_id=payload.parent_span_id,
        name=payload.name,
        span_type=payload.span_type,
        input=payload.input,
        model=payload.model,
        status="running",
        metadata_=payload.metadata,
        started_at=time.time(),
    )
    db.add(span)
    await db.commit()
    return {"span_id": span_id, "trace_id": trace_id}


@router.post("/{trace_id}/spans/{span_id}/end")
@limiter.limit("300/minute")
async def end_span(
    request: Request,
    trace_id: str,
    span_id: str,
    payload: EndSpanPayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    ensure_role(ctx, "admin", "analyst")
    # Verify trace belongs to this api_key
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.api_key == plan_ctx.key))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="trace not found")

    result = await db.execute(select(Span).where(Span.id == span_id, Span.trace_id == trace_id))
    span = result.scalar_one_or_none()
    if not span:
        raise HTTPException(status_code=404, detail="span not found")

    now = time.time()
    span.status = payload.status
    span.output = payload.output
    span.error = payload.error
    span.tokens = payload.tokens
    if payload.cost_usd is not None:
        span.cost_usd = payload.cost_usd
    else:
        # Keep stored trace costs useful even if caller only sends tokens.
        try:
            if payload.tokens is not None:
                total = max(0, int(float(payload.tokens)))
                est_input = int(total * 0.6)
                est_output = max(0, total - est_input)
                computed = compute_cost_from_tokens(span.model, est_input, est_output)
                if computed is not None:
                    span.cost_usd = computed
        except Exception:
            pass
    span.ended_at = now
    span.duration_ms = round((now - span.started_at) * 1000, 1)

    await db.commit()
    return {"span_id": span_id, "status": span.status, "duration_ms": span.duration_ms}


# ── List & Search ─────────────────────────────────────────────────────────────

@router.get("")
async def list_traces(
    name: str | None = Query(None),
    status: str | None = Query(None),
    from_ts: float | None = Query(None),
    to_ts: float | None = Query(None),
    min_duration_ms: float | None = Query(None),
    min_cost_usd: float | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    query = select(Trace).where(Trace.api_key == plan_ctx.key).order_by(Trace.started_at.desc())
    if name:
        query = query.where(Trace.name.contains(name))
    if status:
        query = query.where(Trace.status == status)
    if from_ts is not None:
        query = query.where(Trace.started_at >= from_ts)
    if to_ts is not None:
        query = query.where(Trace.started_at <= to_ts)
    if min_duration_ms is not None:
        query = query.where(Trace.total_duration_ms >= min_duration_ms)
    result = await db.execute(query.offset(offset).limit(limit))
    traces = result.scalars().all()

    trace_ids = [t.id for t in traces]
    span_counts: dict[str, int] = {}
    span_cost_totals: dict[str, float] = {}
    span_token_totals: dict[str, float] = {}
    if trace_ids:
        counts_result = await db.execute(
            select(Span.trace_id, func.count(Span.id).label("cnt"))
            .where(Span.trace_id.in_(trace_ids))
            .group_by(Span.trace_id)
        )
        span_counts = {row.trace_id: row.cnt for row in counts_result}
        spans_result = await db.execute(select(Span).where(Span.trace_id.in_(trace_ids)))
        for s in spans_result.scalars().all():
            span_cost_totals[s.trace_id] = span_cost_totals.get(s.trace_id, 0.0) + _span_effective_cost(s)
            span_token_totals[s.trace_id] = span_token_totals.get(s.trace_id, 0.0) + float(s.tokens or 0.0)

    items = []
    for t in traces:
        effective_cost = round(span_cost_totals.get(t.id, float(t.total_cost_usd or 0.0)), 6)
        if min_cost_usd is not None and effective_cost < min_cost_usd:
            continue
        items.append({
            "trace_id": t.id,
            "name": t.name,
            "status": t.status,
            "input_preview": (t.input or "")[:120],
            "output_preview": (t.output or "")[:120],
            "total_tokens": span_token_totals.get(t.id, float(t.total_tokens or 0.0)),
            "total_cost_usd": effective_cost,
            "total_duration_ms": t.total_duration_ms,
            "span_count": span_counts.get(t.id, 0),
            "error": t.error,
            "started_at": t.started_at,
            "ended_at": t.ended_at,
        })

    return {"traces": items, "count": len(items), "offset": offset, "limit": limit}


@router.delete("/{trace_id}")
async def delete_trace(
    trace_id: str,
    _admin: None = Depends(require_admin_token),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    spans_result = await db.execute(select(Span).where(Span.trace_id == trace_id))
    spans = spans_result.scalars().all()
    for span in spans:
        await db.delete(span)
    await db.delete(trace)
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            action="trace_delete",
            detail=f"trace_id={trace_id} spans_deleted={len(spans)}",
            timestamp=time.time(),
        )
    )
    await db.commit()
    return {"deleted": True, "trace_id": trace_id, "spans_deleted": len(spans)}


@router.get("/{trace_id}")
async def get_trace_detail(
    trace_id: str,
    db: AsyncSession = Depends(get_session),
    plan_ctx: PlanContext = Depends(require_feature("agent_debugger")),
):
    result = await db.execute(select(Trace).where(Trace.id == trace_id, Trace.api_key == plan_ctx.key))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    spans_result = await db.execute(
        select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at)
    )
    spans = spans_result.scalars().all()
    total_tokens = sum(float(s.tokens or 0.0) for s in spans)
    total_cost = round(sum(_span_effective_cost(s) for s in spans), 6)

    return {
        "trace_id": trace.id,
        "name": trace.name,
        "status": trace.status,
        "input": trace.input,
        "output": trace.output,
        "total_tokens": total_tokens if spans else trace.total_tokens,
        "total_cost_usd": total_cost if spans else trace.total_cost_usd,
        "total_duration_ms": trace.total_duration_ms,
        "error": trace.error,
        "metadata": trace.metadata_,
        "started_at": trace.started_at,
        "ended_at": trace.ended_at,
        "spans": [
            {
                "span_id": s.id,
                "parent_span_id": s.parent_span_id,
                "name": s.name,
                "span_type": s.span_type,
                "status": s.status,
                "input": s.input,
                "output": s.output,
                "model": s.model,
                "tokens": s.tokens,
                "cost_usd": round(_span_effective_cost(s), 8),
                "duration_ms": s.duration_ms,
                "error": s.error,
                "metadata": s.metadata_,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
            }
            for s in spans
        ],
    }
