"""
In-process async queue (mock for Redis/Kafka).
Drop-in replacement: swap _queue for an actual broker client later.
"""
import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
_task: asyncio.Task | None = None
_semaphore: asyncio.Semaphore = asyncio.Semaphore(8)


async def enqueue(message: dict[str, Any]) -> None:
    try:
        _queue.put_nowait(message)
    except asyncio.QueueFull:
        logger.warning("Evaluation queue full — dropping message %s", message.get("request_id"))


async def _process(message: dict[str, Any]) -> None:
    from evaluation.engine import evaluate_request
    from storage.database import get_session_ctx
    from storage.models import Evaluation

    request_id = message["request_id"]
    try:
        async with get_session_ctx() as db:
            from storage.models import Request
            from sqlalchemy import select

            result = await db.execute(select(Request).where(Request.id == request_id))
            req = result.scalar_one_or_none()
            if req is None:
                logger.warning("Request %s not found in DB", request_id)
                return

            eval_result = await asyncio.to_thread(
                evaluate_request, req.input, req.output, req.prompt
            )

            ev = Evaluation(
                request_id=request_id,
                quality_score=eval_result["quality_score"],
                hallucination_score=eval_result["hallucination_score"],
                flags=eval_result["flags"],
                score_explanation=eval_result["explanation"],
            )
            db.add(ev)
            await db.commit()
            logger.info("Evaluated %s → quality=%.2f", request_id, eval_result["quality_score"])

            # Check budget alert
            await _check_budget_alert(db)
    except Exception:
        logger.exception("Error processing request %s", request_id)


async def _check_budget_alert(db) -> None:
    """Fire webhook if daily spend exceeds the configured budget."""
    try:
        from sqlalchemy import select, text
        from storage.models import BudgetAlert

        result = await db.execute(select(BudgetAlert).where(BudgetAlert.id == "default"))
        alert = result.scalar_one_or_none()
        if not alert or alert.triggered_today:
            return

        sql = text("""
            SELECT COALESCE(SUM(CAST(json_extract(r.metadata, '$.cost_usd') AS REAL)), 0) AS spent
            FROM requests r
            WHERE r.timestamp >= strftime('%s', 'now', 'start of day')
        """)
        row = (await db.execute(sql)).one()
        spent = row.spent

        if spent >= alert.daily_budget_usd:
            alert.triggered_today = True
            alert.last_triggered = time.time()
            await db.commit()
            logger.warning("Budget alert triggered: $%.4f spent of $%.2f budget", spent, alert.daily_budget_usd)

            if alert.webhook_url:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.post(alert.webhook_url, json={
                            "alert": "budget_exceeded",
                            "daily_budget_usd": alert.daily_budget_usd,
                            "spent_today_usd": round(spent, 4),
                            "percent_used": round(spent / alert.daily_budget_usd * 100, 1),
                            "timestamp": time.time(),
                        })
                except Exception:
                    logger.exception("Failed to send webhook for budget alert")
    except Exception:
        logger.exception("Budget alert check failed")


async def _process_bounded(message: dict[str, Any]) -> None:
    async with _semaphore:
        try:
            await _process(message)
        finally:
            _queue.task_done()


async def _worker_loop() -> None:
    while True:
        message = await _queue.get()
        asyncio.create_task(_process_bounded(message))


async def start_worker() -> None:
    global _task
    _task = asyncio.create_task(_worker_loop())
    logger.info("Queue worker started")


async def stop_worker() -> None:
    if _task:
        try:
            await asyncio.wait_for(_queue.join(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Worker shutdown: queue drain timed out")
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
