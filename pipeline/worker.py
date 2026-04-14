"""
In-process async queue (mock for Redis/Kafka).
Drop-in replacement: swap _queue for an actual broker client later.
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_task: asyncio.Task | None = None


async def enqueue(message: dict[str, Any]) -> None:
    await _queue.put(message)


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

            eval_result = evaluate_request(req.input, req.output, req.prompt)

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
    except Exception:
        logger.exception("Error processing request %s", request_id)


async def _worker_loop() -> None:
    while True:
        message = await _queue.get()
        asyncio.create_task(_process(message))
        _queue.task_done()


async def start_worker() -> None:
    global _task
    _task = asyncio.create_task(_worker_loop())
    logger.info("Queue worker started")


async def stop_worker() -> None:
    if _task:
        _task.cancel()
