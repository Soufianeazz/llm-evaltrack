"""
Prompt debugging endpoints — search, filter, and inspect individual LLM calls.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_api_key
from storage.database import get_session
from storage.models import Evaluation, Request

router = APIRouter(prefix="/debug")


@router.get("/requests")
async def search_requests(
    model: str | None = Query(None),
    user_id: str | None = Query(None),
    flag: str | None = Query(None),
    max_quality: float | None = Query(None, ge=0.0, le=1.0),
    min_quality: float | None = Query(None, ge=0.0, le=1.0),
    prompt_contains: str | None = Query(None),
    input_contains: str | None = Query(None),
    output_contains: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    api_key: str = Depends(require_api_key),
):
    query = (
        select(Request, Evaluation)
        .outerjoin(Evaluation, Evaluation.request_id == Request.id)
        .where(Request.api_key == api_key)
        .order_by(Request.timestamp.desc())
    )

    if model:
        query = query.where(Request.model == model)
    if prompt_contains:
        query = query.where(Request.prompt.contains(prompt_contains))
    if input_contains:
        query = query.where(Request.input.contains(input_contains))
    if output_contains:
        query = query.where(Request.output.contains(output_contains))
    if max_quality is not None:
        query = query.where(Evaluation.quality_score <= max_quality)
    if min_quality is not None:
        query = query.where(Evaluation.quality_score >= min_quality)
    if flag:
        query = query.where(Evaluation.flags.contains(flag))

    result = await db.execute(query.offset(offset).limit(limit))
    rows = result.all()

    items = []
    for req, ev in rows:
        meta = req.metadata_ or {}
        if user_id and meta.get("user_id") != user_id:
            continue
        items.append({
            "request_id": req.id,
            "model": req.model,
            "timestamp": req.timestamp,
            "input_preview": req.input[:150],
            "output_preview": req.output[:150],
            "prompt_preview": req.prompt[:100],
            "quality_score": ev.quality_score if ev else None,
            "hallucination_score": ev.hallucination_score if ev else None,
            "flags": ev.flags if ev else [],
            "cost_usd": meta.get("cost_usd"),
            "user_id": meta.get("user_id"),
            "metadata": meta,
        })

    return {"results": items, "count": len(items)}


@router.get("/requests/{request_id}")
async def get_request_detail(
    request_id: str,
    db: AsyncSession = Depends(get_session),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        select(Request, Evaluation)
        .outerjoin(Evaluation, Evaluation.request_id == Request.id)
        .where(Request.id == request_id, Request.api_key == api_key)
    )
    row = result.one_or_none()
    if not row:
        return {"error": "not found"}

    req, ev = row
    meta = req.metadata_ or {}

    return {
        "request_id": req.id,
        "model": req.model,
        "timestamp": req.timestamp,
        "input": req.input,
        "output": req.output,
        "prompt": req.prompt,
        "metadata": meta,
        "cost_usd": meta.get("cost_usd"),
        "input_tokens": meta.get("input_tokens"),
        "output_tokens": meta.get("output_tokens"),
        "evaluation": {
            "quality_score": ev.quality_score,
            "hallucination_score": ev.hallucination_score,
            "flags": ev.flags,
            "explanation": ev.score_explanation,
        } if ev else None,
    }


@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_session),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        text("SELECT DISTINCT model FROM requests WHERE api_key = :api_key ORDER BY model"),
        {"api_key": api_key},
    )
    return [row[0] for row in result]


@router.get("/flags")
async def list_flags(
    db: AsyncSession = Depends(get_session),
    api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        select(Evaluation.flags)
        .join(Request, Request.id == Evaluation.request_id)
        .where(Request.api_key == api_key)
    )
    all_flags = set()
    for (flags,) in result:
        if flags:
            for f in flags:
                all_flags.add(f)
    return sorted(all_flags)
