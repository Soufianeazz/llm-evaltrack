"""
In-process async queue (mock for Redis/Kafka).
Drop-in replacement: swap _queue for an actual broker client later.
"""
import asyncio
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def _airgap_enabled() -> bool:
    return os.environ.get("AGENTLENS_AIRGAP", "").strip() in ("1", "true", "True", "yes")


def _is_local_url(url: str) -> bool:
    """Allow only loopback/private webhooks in air-gap mode (e.g. internal Slack relay)."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    # RFC1918 and link-local — safe internal-only addresses.
    return (
        host.startswith("10.")
        or host.startswith("192.168.")
        or host.startswith("169.254.")
        or any(host.startswith(f"172.{i}.") for i in range(16, 32))
    )

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
                if _airgap_enabled() and not _is_local_url(alert.webhook_url):
                    logger.info(
                        "Air-gap mode: skipping budget webhook to non-local URL %s",
                        alert.webhook_url,
                    )
                    return
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        percent_used = round(spent / alert.daily_budget_usd * 100, 1)
                        payload = {
                            # Slack incoming webhooks require a text field.
                            "text": (
                                f":rotating_light: AgentLens budget alert triggered\\n"
                                f"Budget: ${alert.daily_budget_usd:.2f}\\n"
                                f"Spent today: ${round(spent, 4):.4f}\\n"
                                f"Usage: {percent_used}%"
                            ),
                            "alert": "budget_exceeded",
                            "daily_budget_usd": alert.daily_budget_usd,
                            "spent_today_usd": round(spent, 4),
                            "percent_used": percent_used,
                            "timestamp": time.time(),
                        }
                        resp = await client.post(alert.webhook_url, json=payload)
                        if resp.status_code >= 400:
                            logger.error(
                                "Budget alert webhook returned error status=%s body=%s",
                                resp.status_code,
                                (resp.text or "")[:500],
                            )
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
