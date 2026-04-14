"""
SDK entry point.
Fire-and-forget: ships data to the API without blocking the caller.
"""
import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_API_URL = "http://localhost:8000/ingest"
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # seconds


async def _send(payload: dict[str, Any], retries: int = _MAX_RETRIES) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(1, retries + 1):
            try:
                r = await client.post(_API_URL, json=payload)
                r.raise_for_status()
                return
            except Exception as exc:
                if attempt == retries:
                    logger.error("track_llm_call failed after %d attempts: %s", retries, exc)
                else:
                    await asyncio.sleep(_RETRY_DELAY * attempt)


def track_llm_call(
    input: str,
    output: str,
    prompt: str,
    model: str,
    metadata: dict[str, Any] | None = None,
    api_url: str = _API_URL,
) -> None:
    """
    Non-blocking: schedules a fire-and-forget coroutine on the running event loop
    (or creates a background thread if no loop is active — covers sync callers).
    """
    payload = {
        "input": input,
        "output": output,
        "prompt": prompt,
        "model": model,
        "metadata": metadata or {},
        "timestamp": time.time(),
    }

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send(payload))
    except RuntimeError:
        # No running loop → caller is synchronous
        asyncio.run(_send(payload))
