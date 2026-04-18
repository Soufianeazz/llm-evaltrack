"""
Agent debugging endpoints — traces and spans for multi-step agent runs.
"""
import os
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from api.limiter import limiter
from storage.database import get_session
from storage.models import Span, Trace

router = APIRouter(prefix="/traces")


def _require_admin(token: str | None):
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


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
async def create_trace(request: Request, payload: CreateTracePayload, db: AsyncSession = Depends(get_session)):
    trace_id = str(uuid.uuid4())
    trace = Trace(
        id=trace_id,
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
async def end_trace(request: Request, trace_id: str, payload: EndTracePayload, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    now = time.time()
    trace.status = payload.status
    trace.output = payload.output
    trace.error = payload.error
    trace.ended_at = now
    trace.total_duration_ms = round((now - trace.started_at) * 1000, 1)

    # Aggregate span stats
    spans_result = await db.execute(select(Span).where(Span.trace_id == trace_id))
    spans = spans_result.scalars().all()
    trace.total_tokens = sum(s.tokens or 0 for s in spans)
    trace.total_cost_usd = sum(s.cost_usd or 0 for s in spans)

    await db.commit()
    return {"trace_id": trace_id, "status": trace.status, "duration_ms": trace.total_duration_ms}


# ── Span CRUD ─────────────────────────────────────────────────────────────────

@router.post("/{trace_id}/spans")
@limiter.limit("300/minute")
async def create_span(request: Request, trace_id: str, payload: CreateSpanPayload, db: AsyncSession = Depends(get_session)):
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
async def end_span(request: Request, trace_id: str, span_id: str, payload: EndSpanPayload, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Span).where(Span.id == span_id, Span.trace_id == trace_id))
    span = result.scalar_one_or_none()
    if not span:
        raise HTTPException(status_code=404, detail="span not found")

    now = time.time()
    span.status = payload.status
    span.output = payload.output
    span.error = payload.error
    span.tokens = payload.tokens
    span.cost_usd = payload.cost_usd
    span.ended_at = now
    span.duration_ms = round((now - span.started_at) * 1000, 1)

    await db.commit()
    return {"span_id": span_id, "status": span.status, "duration_ms": span.duration_ms}


# ── List & Search ─────────────────────────────────────────────────────────────

@router.get("")
async def list_traces(
    name: str | None = Query(None),
    status: str | None = Query(None),
    from_ts: float | None = Query(None, description="Unix timestamp — only traces started after this"),
    to_ts: float | None = Query(None, description="Unix timestamp — only traces started before this"),
    min_duration_ms: float | None = Query(None, description="Only traces slower than this (ms)"),
    min_cost_usd: float | None = Query(None, description="Only traces more expensive than this (USD)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    query = select(Trace).order_by(Trace.started_at.desc())
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
    if min_cost_usd is not None:
        query = query.where(Trace.total_cost_usd >= min_cost_usd)

    result = await db.execute(query.offset(offset).limit(limit))
    traces = result.scalars().all()

    # Single query for all span counts
    trace_ids = [t.id for t in traces]
    span_counts: dict[str, int] = {}
    if trace_ids:
        counts_result = await db.execute(
            select(Span.trace_id, func.count(Span.id).label("cnt"))
            .where(Span.trace_id.in_(trace_ids))
            .group_by(Span.trace_id)
        )
        span_counts = {row.trace_id: row.cnt for row in counts_result}

    items = []
    for t in traces:
        items.append({
            "trace_id": t.id,
            "name": t.name,
            "status": t.status,
            "input_preview": (t.input or "")[:120],
            "output_preview": (t.output or "")[:120],
            "total_tokens": t.total_tokens,
            "total_cost_usd": t.total_cost_usd,
            "total_duration_ms": t.total_duration_ms,
            "span_count": span_counts.get(t.id, 0),
            "error": t.error,
            "started_at": t.started_at,
            "ended_at": t.ended_at,
        })

    return {"traces": items, "count": len(items), "offset": offset, "limit": limit}


@router.delete("/{trace_id}")
async def delete_trace(trace_id: str, token: str = Query(...), db: AsyncSession = Depends(get_session)):
    _require_admin(token)
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    spans_result = await db.execute(select(Span).where(Span.trace_id == trace_id))
    spans = spans_result.scalars().all()
    span_count = len(spans)
    for span in spans:
        await db.delete(span)
    await db.delete(trace)
    await db.commit()
    return {"deleted": True, "trace_id": trace_id, "spans_deleted": span_count}


@router.get("/{trace_id}")
async def get_trace_detail(trace_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="trace not found")

    spans_result = await db.execute(
        select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at)
    )
    spans = spans_result.scalars().all()

    return {
        "trace_id": trace.id,
        "name": trace.name,
        "status": trace.status,
        "input": trace.input,
        "output": trace.output,
        "total_tokens": trace.total_tokens,
        "total_cost_usd": trace.total_cost_usd,
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
                "cost_usd": s.cost_usd,
                "duration_ms": s.duration_ms,
                "error": s.error,
                "metadata": s.metadata_,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
            }
            for s in spans
        ],
    }
