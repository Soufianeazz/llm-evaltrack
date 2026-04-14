"""
Read endpoints consumed by the dashboard.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import get_session
from storage.models import Evaluation, Request

router = APIRouter()


@router.get("/requests/worst")
async def worst_responses(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """Return requests ordered by quality_score ascending (worst first)."""
    result = await db.execute(
        select(Request, Evaluation)
        .join(Evaluation, Evaluation.request_id == Request.id)
        .order_by(Evaluation.quality_score.asc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "request_id": req.id,
            "model": req.model,
            "timestamp": req.timestamp,
            "quality_score": ev.quality_score,
            "hallucination_score": ev.hallucination_score,
            "flags": ev.flags,
            "score_explanation": ev.score_explanation,
            "input_preview": req.input[:120],
            "output_preview": req.output[:120],
        }
        for req, ev in rows
    ]


@router.get("/requests/trend")
async def quality_trend(db: AsyncSession = Depends(get_session)):
    """Average quality score bucketed by hour (last 24 h)."""
    sql = text(
        """
        SELECT
            strftime('%Y-%m-%dT%H:00:00', datetime(r.timestamp, 'unixepoch')) AS hour,
            AVG(e.quality_score) AS avg_quality
        FROM requests r
        JOIN evaluations e ON e.request_id = r.id
        WHERE r.timestamp >= strftime('%s','now','-1 day')
        GROUP BY hour
        ORDER BY hour ASC
        """
    )
    result = await db.execute(sql)
    return [{"hour": row.hour, "avg_quality": row.avg_quality} for row in result]


@router.get("/requests/clusters")
async def bad_response_clusters(
    quality_threshold: float = Query(0.7, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_session),
):
    """
    Group bad responses (below quality_threshold) by their primary flag.
    Returns each category with count, avg quality, and avg hallucination score.
    """
    result = await db.execute(
        select(Evaluation).where(Evaluation.quality_score < quality_threshold)
    )
    evaluations = result.scalars().all()

    clusters: dict[str, dict] = {}
    for ev in evaluations:
        flags = ev.flags or ["unflagged"]
        primary = flags[0] if flags else "unflagged"
        if primary not in clusters:
            clusters[primary] = {
                "category": primary,
                "count": 0,
                "total_quality": 0.0,
                "total_hallucination": 0.0,
            }
        clusters[primary]["count"] += 1
        clusters[primary]["total_quality"] += ev.quality_score
        clusters[primary]["total_hallucination"] += ev.hallucination_score

    result_list = []
    for c in sorted(clusters.values(), key=lambda x: -x["count"]):
        n = c["count"]
        result_list.append({
            "category": c["category"],
            "count": n,
            "avg_quality": round(c["total_quality"] / n, 3),
            "avg_hallucination": round(c["total_hallucination"] / n, 3),
        })

    return result_list


@router.get("/requests/root-cause")
async def root_cause_analysis(
    quality_threshold: float = Query(0.6, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_session),
):
    """
    Find which prompts are responsible for the most bad responses.
    Groups by prompt prefix (first 80 chars) and returns failure rate + avg quality.
    """
    result = await db.execute(
        select(Request, Evaluation).join(Evaluation, Evaluation.request_id == Request.id)
    )
    rows = result.all()

    prompt_stats: dict[str, dict] = {}
    for req, ev in rows:
        key = req.prompt[:80].strip()
        if key not in prompt_stats:
            prompt_stats[key] = {"prompt": req.prompt[:120], "total": 0, "failures": 0,
                                  "total_quality": 0.0, "total_cost": 0.0, "models": set()}
        prompt_stats[key]["total"] += 1
        prompt_stats[key]["total_quality"] += ev.quality_score
        prompt_stats[key]["models"].add(req.model)
        cost = (req.metadata_ or {}).get("cost_usd", 0)
        prompt_stats[key]["total_cost"] += cost
        if ev.quality_score < quality_threshold:
            prompt_stats[key]["failures"] += 1

    result_list = []
    for s in prompt_stats.values():
        n = s["total"]
        failure_rate = s["failures"] / n if n > 0 else 0
        result_list.append({
            "prompt_preview": s["prompt"],
            "total_calls": n,
            "failure_rate": round(failure_rate, 3),
            "avg_quality": round(s["total_quality"] / n, 3),
            "total_cost_usd": round(s["total_cost"], 4),
            "models": list(s["models"]),
        })

    return sorted(result_list, key=lambda x: -x["failure_rate"])[:10]


@router.get("/requests/cost-quality")
async def cost_quality_correlation(db: AsyncSession = Depends(get_session)):
    """Per-model: avg quality score vs avg cost per call."""
    result = await db.execute(
        select(Request, Evaluation).join(Evaluation, Evaluation.request_id == Request.id)
    )
    rows = result.all()

    models: dict[str, dict] = {}
    for req, ev in rows:
        m = req.model
        if m not in models:
            models[m] = {"total": 0, "total_quality": 0.0, "total_cost": 0.0, "failures": 0}
        cost = (req.metadata_ or {}).get("cost_usd", 0)
        models[m]["total"] += 1
        models[m]["total_quality"] += ev.quality_score
        models[m]["total_cost"] += cost
        if ev.quality_score < 0.6:
            models[m]["failures"] += 1

    result_list = []
    for model, s in models.items():
        n = s["total"]
        result_list.append({
            "model": model,
            "avg_quality": round(s["total_quality"] / n, 3),
            "avg_cost_usd": round(s["total_cost"] / n, 6),
            "total_calls": n,
            "failure_rate": round(s["failures"] / n, 3),
        })

    return sorted(result_list, key=lambda x: -x["avg_quality"])


@router.get("/requests/stats")
async def overview_stats(db: AsyncSession = Depends(get_session)):
    """Top-level KPIs for the dashboard header."""
    sql = text("""
        SELECT
            COUNT(*) AS total_calls,
            AVG(e.quality_score) AS avg_quality,
            SUM(CAST(json_extract(r.metadata, '$.cost_usd') AS REAL)) AS total_cost,
            COUNT(CASE WHEN e.quality_score < 0.6 THEN 1 END) AS bad_calls
        FROM requests r
        JOIN evaluations e ON e.request_id = r.id
        WHERE r.timestamp >= strftime('%s','now','-1 day')
    """)
    row = (await db.execute(sql)).one()
    total = row.total_calls or 0
    return {
        "total_calls_24h": total,
        "avg_quality_24h": round(row.avg_quality or 0, 3),
        "total_cost_24h_usd": round(row.total_cost or 0, 4),
        "bad_response_rate": round((row.bad_calls or 0) / total, 3) if total > 0 else 0,
    }


@router.get("/requests/regression")
async def regression_detection(
    window_minutes: int = Query(60, ge=5, le=1440),
    threshold: float = Query(0.1, ge=0.01, le=1.0),
    db: AsyncSession = Depends(get_session),
):
    """
    Compare quality in the current window vs the previous window of equal length.
    Returns a regression alert if avg quality dropped by more than `threshold`.
    """
    sql = text(
        """
        SELECT
            AVG(CASE WHEN r.timestamp >= strftime('%s','now',:neg_window) THEN e.quality_score END) AS current_avg,
            AVG(CASE WHEN r.timestamp >= strftime('%s','now',:neg_double)
                      AND r.timestamp <  strftime('%s','now',:neg_window) THEN e.quality_score END) AS previous_avg,
            COUNT(CASE WHEN r.timestamp >= strftime('%s','now',:neg_window) THEN 1 END) AS current_count,
            COUNT(CASE WHEN r.timestamp >= strftime('%s','now',:neg_double)
                        AND r.timestamp < strftime('%s','now',:neg_window) THEN 1 END) AS previous_count
        FROM requests r
        JOIN evaluations e ON e.request_id = r.id
        WHERE r.timestamp >= strftime('%s','now',:neg_double)
        """
    )
    neg_window = f"-{window_minutes} minutes"
    neg_double = f"-{window_minutes * 2} minutes"
    row = (await db.execute(sql, {"neg_window": neg_window, "neg_double": neg_double})).one()

    current_avg = row.current_avg
    previous_avg = row.previous_avg

    if current_avg is None or previous_avg is None:
        return {
            "regression_detected": False,
            "reason": "not enough data in one or both windows",
            "current_avg": current_avg,
            "previous_avg": previous_avg,
            "current_count": row.current_count,
            "previous_count": row.previous_count,
            "window_minutes": window_minutes,
        }

    drop = previous_avg - current_avg
    regression = drop >= threshold

    return {
        "regression_detected": regression,
        "reason": f"quality dropped by {drop:.3f} (threshold {threshold})" if regression else "quality stable",
        "current_avg": round(current_avg, 3),
        "previous_avg": round(previous_avg, 3),
        "drop": round(drop, 3),
        "current_count": row.current_count,
        "previous_count": row.previous_count,
        "window_minutes": window_minutes,
    }
