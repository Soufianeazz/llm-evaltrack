"""
Agent debugging endpoints — traces and spans for multi-step agent runs.
"""
import time
import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from storage.database import get_session
from storage.models import Span, Trace

router = APIRouter(prefix="/traces")


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
async def create_trace(payload: CreateTracePayload, db: AsyncSession = Depends(get_session)):
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
async def end_trace(trace_id: str, payload: EndTracePayload, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        return {"error": "trace not found"}

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
async def create_span(trace_id: str, payload: CreateSpanPayload, db: AsyncSession = Depends(get_session)):
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
async def end_span(trace_id: str, span_id: str, payload: EndSpanPayload, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Span).where(Span.id == span_id, Span.trace_id == trace_id))
    span = result.scalar_one_or_none()
    if not span:
        return {"error": "span not found"}

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
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    query = select(Trace).order_by(Trace.started_at.desc())
    if name:
        query = query.where(Trace.name.contains(name))
    if status:
        query = query.where(Trace.status == status)

    result = await db.execute(query.limit(limit))
    traces = result.scalars().all()

    # Get span counts
    items = []
    for t in traces:
        count_result = await db.execute(
            select(func.count()).where(Span.trace_id == t.id)
        )
        span_count = count_result.scalar()

        items.append({
            "trace_id": t.id,
            "name": t.name,
            "status": t.status,
            "input_preview": (t.input or "")[:120],
            "output_preview": (t.output or "")[:120],
            "total_tokens": t.total_tokens,
            "total_cost_usd": t.total_cost_usd,
            "total_duration_ms": t.total_duration_ms,
            "span_count": span_count,
            "error": t.error,
            "started_at": t.started_at,
            "ended_at": t.ended_at,
        })

    return {"traces": items, "count": len(items)}


@router.get("/{trace_id}")
async def get_trace_detail(trace_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        return {"error": "trace not found"}

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
