"""
OpenAI auto-instrumentation.

After calling patch(), every openai.chat.completions.create() call
is automatically tracked — no changes to existing code required.

Supports both sync and async clients.
"""
from __future__ import annotations

import logging
from typing import Any

from agentlens.tracker import track_llm_call

logger = logging.getLogger(__name__)

_patched = False


def patch() -> None:
    """
    Monkey-patch the OpenAI SDK to auto-track all chat completion calls.
    Call once at application startup, after agentlens.init().

    Requires: pip install openai
    """
    global _patched
    if _patched:
        return

    try:
        import openai
    except ImportError:
        raise ImportError(
            "openai package not found. Install it with: pip install openai"
        )

    # ── Sync client ──────────────────────────────────────────────────────────
    from openai.resources.chat.completions import Completions

    _orig_create = Completions.create

    def _tracked_create(self: Any, **kwargs: Any):
        response = _orig_create(self, **kwargs)
        _ship_openai(kwargs, response)
        return response

    Completions.create = _tracked_create  # type: ignore[method-assign]

    # ── Async client ─────────────────────────────────────────────────────────
    from openai.resources.chat.completions import AsyncCompletions

    _orig_acreate = AsyncCompletions.create

    async def _tracked_acreate(self: Any, **kwargs: Any):
        response = await _orig_acreate(self, **kwargs)
        _ship_openai(kwargs, response)
        return response

    AsyncCompletions.create = _tracked_acreate  # type: ignore[method-assign]

    _patched = True
    logger.info("llm-observe: OpenAI instrumentation active")


def _ship_openai(kwargs: dict, response: Any) -> None:
    """Extract fields from an OpenAI ChatCompletion response and track it."""
    try:
        messages = kwargs.get("messages", [])
        # Last user message as input
        user_msgs = [m for m in messages if m.get("role") == "user"]
        input_text = user_msgs[-1].get("content", "") if user_msgs else ""
        # System prompt
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        prompt_text = sys_msgs[0].get("content", "") if sys_msgs else ""

        choice = response.choices[0]
        output_text = choice.message.content or ""
        model = response.model or kwargs.get("model", "unknown")

        usage = getattr(response, "usage", None)
        metadata: dict = {"finish_reason": choice.finish_reason}
        if usage:
            metadata["input_tokens"] = usage.prompt_tokens
            metadata["output_tokens"] = usage.completion_tokens
            # Rough cost estimate — real costs depend on your plan
            metadata["cost_usd"] = _estimate_cost_openai(model, usage)

        track_llm_call(
            input=input_text,
            output=output_text,
            prompt=prompt_text,
            model=model,
            metadata=metadata,
        )
    except Exception as exc:
        logger.debug("llm-observe: OpenAI tracking error (non-fatal): %s", exc)


_OPENAI_COSTS_PER_1M = {
    "gpt-4o":       {"input": 5.0,  "output": 15.0},
    "gpt-4o-mini":  {"input": 0.15, "output": 0.6},
    "gpt-4-turbo":  {"input": 10.0, "output": 30.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
}


def _estimate_cost_openai(model: str, usage: Any) -> float:
    for key, rates in _OPENAI_COSTS_PER_1M.items():
        if model.startswith(key):
            cost = (
                usage.prompt_tokens * rates["input"] / 1_000_000
                + usage.completion_tokens * rates["output"] / 1_000_000
            )
            return round(cost, 8)
    return 0.0
