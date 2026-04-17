"""
Core tracker — fire-and-forget HTTP shipping with retry.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Global config — set once via init()
_config: dict[str, Any] = {
    "api_url": "http://localhost:8000/ingest",
    "api_key": None,
    "max_retries": 3,
    "timeout": 5.0,
    "enabled": True,
}


def init(
    api_url: str = "http://localhost:8000/ingest",
    api_key: str | None = None,
    max_retries: int = 3,
    timeout: float = 5.0,
    enabled: bool = True,
) -> None:
    """
    Configure the SDK once at application startup.

    Args:
        api_url:     URL of your agentlens ingest endpoint.
        api_key:     Optional bearer token if your server requires auth.
        max_retries: How many times to retry on network failure.
        timeout:     HTTP timeout in seconds.
        enabled:     Set to False to disable all tracking (e.g. in tests).
    """
    _config.update(
        api_url=api_url,
        api_key=api_key,
        max_retries=max_retries,
        timeout=timeout,
        enabled=enabled,
    )
    logger.debug("agentlens configured: api_url=%s enabled=%s", api_url, enabled)


async def _send(payload: dict[str, Any]) -> None:
    headers = {}
    if _config["api_key"]:
        headers["Authorization"] = f"Bearer {_config['api_key']}"

    async with httpx.AsyncClient(timeout=_config["timeout"]) as client:
        for attempt in range(1, _config["max_retries"] + 1):
            try:
                r = await client.post(_config["api_url"], json=payload, headers=headers)
                r.raise_for_status()
                return
            except Exception as exc:
                if attempt == _config["max_retries"]:
                    logger.error("agentlens: failed after %d attempts: %s", attempt, exc)
                else:
                    await asyncio.sleep(attempt * 1.0)


def track_llm_call(
    input: str,
    output: str,
    prompt: str = "",
    model: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Track a single LLM call. Non-blocking — safe to call anywhere.

    Args:
        input:    The user message / input sent to the model.
        output:   The model's response text.
        prompt:   System prompt or instruction used.
        model:    Model identifier (e.g. "gpt-4o", "claude-opus-4-6").
        metadata: Any extra key/value pairs (cost_usd, tokens, feature, etc.).
    """
    if not _config["enabled"]:
        return

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
        asyncio.run(_send(payload))
