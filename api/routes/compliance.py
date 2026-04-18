"""
Compliance endpoints — data export, retention, deletion, audit log.
"""
import csv
import io
import os
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import AuditLog, Evaluation, Request, RetentionPolicy

router = APIRouter(prefix="/compliance")


def _require_admin(token: str | None):
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


async def _log_action(db: AsyncSession, action: str, detail: str) -> None:
    entry = AuditLog(id=str(uuid.uuid4()), action=action, detail=detail, timestamp=time.time())
    db.add(entry)
    await db.commit()


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/export")
async def export_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    days: int | None = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
):
    """Export all LLM call data as JSON or CSV."""
    query = (
        select(Request, Evaluation)
        .outerjoin(Evaluation, Evaluation.request_id == Request.id)
        .order_by(Request.timestamp.desc())
    )
    if days:
        cutoff = time.time() - (days * 86400)
        query = query.where(Request.timestamp >= cutoff)

    result = await db.execute(query)
    rows = result.all()

    records = []
    for req, ev in rows:
        meta = req.metadata_ or {}
        records.append({
            "request_id": req.id,
            "timestamp": req.timestamp,
            "model": req.model,
            "input": req.input,
            "output": req.output,
            "prompt": req.prompt,
            "cost_usd": meta.get("cost_usd"),
            "input_tokens": meta.get("input_tokens"),
            "output_tokens": meta.get("output_tokens"),
            "quality_score": ev.quality_score if ev else None,
            "hallucination_score": ev.hallucination_score if ev else None,
            "flags": ev.flags if ev else [],
            "explanation": ev.score_explanation if ev else None,
        })

    await _log_action(db, "export", f"Exported {len(records)} records as {format}")

    if format == "csv":
        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=llm-evaltrack-export.csv"},
        )

    return {"records": records, "count": len(records)}


# ── Delete individual requests (GDPR right to erasure) ───────────────────────

@router.delete("/requests/{request_id}")
async def delete_request(request_id: str, token: str = Query(...), db: AsyncSession = Depends(get_session)):
    _require_admin(token)
    """Delete a single request and its evaluation — GDPR right to erasure."""
    await db.execute(delete(Evaluation).where(Evaluation.request_id == request_id))
    result = await db.execute(delete(Request).where(Request.id == request_id))
    await db.commit()

    if result.rowcount == 0:
        return {"deleted": False, "reason": "not found"}

    await _log_action(db, "delete", f"Deleted request {request_id}")
    return {"deleted": True, "request_id": request_id}


@router.delete("/requests")
async def delete_requests_bulk(
    older_than_days: int = Query(..., ge=1, le=365),
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    """Bulk-delete all requests older than X days."""
    cutoff = time.time() - (older_than_days * 86400)

    # Get IDs first for cascade delete
    result = await db.execute(
        select(Request.id).where(Request.timestamp < cutoff)
    )
    ids = [row[0] for row in result]

    if ids:
        await db.execute(delete(Evaluation).where(Evaluation.request_id.in_(ids)))
        await db.execute(delete(Request).where(Request.id.in_(ids)))
        await db.commit()

    await _log_action(db, "delete", f"Bulk-deleted {len(ids)} requests older than {older_than_days} days")
    return {"deleted_count": len(ids)}


# ── Retention policy ──────────────────────────────────────────────────────────

@router.post("/retention")
async def set_retention_policy(
    retention_days: int = Query(..., ge=1, le=365),
    enabled: bool = Query(True),
    token: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    _require_admin(token)
    """Set or update the automatic retention policy."""
    result = await db.execute(select(RetentionPolicy).where(RetentionPolicy.id == "default"))
    policy = result.scalar_one_or_none()

    if policy:
        policy.retention_days = retention_days
        policy.enabled = enabled
    else:
        policy = RetentionPolicy(id="default", retention_days=retention_days, enabled=enabled)
        db.add(policy)

    await db.commit()
    await _log_action(db, "policy_change", f"Retention set to {retention_days} days, enabled={enabled}")
    return {"retention_days": retention_days, "enabled": enabled}


@router.get("/retention")
async def get_retention_policy(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(RetentionPolicy).where(RetentionPolicy.id == "default"))
    policy = result.scalar_one_or_none()
    if not policy:
        return {"configured": False}
    return {
        "retention_days": policy.retention_days,
        "enabled": policy.enabled,
        "last_run": policy.last_run,
    }


@router.post("/retention/run")
async def run_retention_now(token: str = Query(...), db: AsyncSession = Depends(get_session)):
    """Manually trigger retention cleanup."""
    _require_admin(token)
    result = await db.execute(select(RetentionPolicy).where(RetentionPolicy.id == "default"))
    policy = result.scalar_one_or_none()
    if not policy or not policy.enabled:
        raise HTTPException(status_code=404, detail="No active retention policy")

    cutoff = time.time() - (policy.retention_days * 86400)
    result = await db.execute(select(Request.id).where(Request.timestamp < cutoff))
    ids = [row[0] for row in result]

    if ids:
        await db.execute(delete(Evaluation).where(Evaluation.request_id.in_(ids)))
        await db.execute(delete(Request).where(Request.id.in_(ids)))

    policy.last_run = time.time()
    await db.commit()

    await _log_action(db, "retention_run", f"Retention cleanup: deleted {len(ids)} records older than {policy.retention_days} days")
    return {"deleted_count": len(ids), "retention_days": policy.retention_days}


# ── Audit log ─────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {"id": e.id, "action": e.action, "detail": e.detail, "timestamp": e.timestamp}
        for e in entries
    ]


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def compliance_stats(db: AsyncSession = Depends(get_session)):
    """Overview stats for the compliance page."""
    total = (await db.execute(text("SELECT COUNT(*) FROM requests"))).scalar()
    oldest = (await db.execute(text("SELECT MIN(timestamp) FROM requests"))).scalar()
    newest = (await db.execute(text("SELECT MAX(timestamp) FROM requests"))).scalar()
    total_evals = (await db.execute(text("SELECT COUNT(*) FROM evaluations"))).scalar()
    audit_count = (await db.execute(text("SELECT COUNT(*) FROM audit_log"))).scalar()

    result = await db.execute(select(RetentionPolicy).where(RetentionPolicy.id == "default"))
    policy = result.scalar_one_or_none()

    return {
        "total_requests": total,
        "total_evaluations": total_evals,
        "oldest_record": oldest,
        "newest_record": newest,
        "audit_log_entries": audit_count,
        "retention_policy": {
            "retention_days": policy.retention_days,
            "enabled": policy.enabled,
            "last_run": policy.last_run,
        } if policy else None,
    }
