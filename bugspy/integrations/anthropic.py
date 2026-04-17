"""
Anthropic auto-instrumentation.

After calling patch(), every anthropic.messages.create() call
is automatically tracked — no changes to existing code required.

Supports both sync and async clients.
"""
from __future__ import annotations

import logging
from typing import Any

from bugspy.tracker import track_llm_call

logger = logging.getLogger(__name__)

_patched = False


def patch() -> None:
    """
    Monkey-patch the Anthropic SDK to auto-track all messages.create() calls.
    Call once at application startup, after agentlens.init().

    Requires: pip install anthropic
    """
    global _patched
    if _patched:
        return

    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package not found. Install it with: pip install anthropic"
        )

    # ── Sync client ──────────────────────────────────────────────────────────
    from anthropic.resources.messages.messages import Messages

    _orig_create = Messages.create

    def _tracked_create(self: Any, **kwargs: Any):
        response = _orig_create(self, **kwargs)
        _ship_anthropic(kwargs, response)
        return response

    Messages.create = _tracked_create  # type: ignore[method-assign]

    # ── Async client ─────────────────────────────────────────────────────────
    from anthropic.resources.messages.messages import AsyncMessages

    _orig_acreate = AsyncMessages.create

    async def _tracked_acreate(self: Any, **kwargs: Any):
        response = await _orig_acreate(self, **kwargs)
        _ship_anthropic(kwargs, response)
        return response

    AsyncMessages.create = _tracked_acreate  # type: ignore[method-assign]

    _patched = True
    logger.info("llm-observe: Anthropic instrumentation active")


def _ship_anthropic(kwargs: dict, response: Any) -> None:
    """Extract fields from an Anthropic Message response and track it."""
    try:
        messages = kwargs.get("messages", [])
        user_msgs = [m for m in messages if m.get("role") == "user"]
        last_user = user_msgs[-1] if user_msgs else {}
        content = last_user.get("content", "")
        if isinstance(content, list):
            # content blocks — grab text blocks only
            input_text = " ".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            )
        else:
            input_text = str(content)

        prompt_text = kwargs.get("system", "")
        if isinstance(prompt_text, list):
            prompt_text = " ".join(
                b.get("text", "") for b in prompt_text if b.get("type") == "text"
            )

        # Extract text from response content blocks (skip thinking blocks)
        output_text = " ".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )

        model = response.model or kwargs.get("model", "unknown")
        usage = getattr(response, "usage", None)
        metadata: dict = {"stop_reason": response.stop_reason}
        if usage:
            metadata["input_tokens"] = usage.input_tokens
            metadata["output_tokens"] = usage.output_tokens
            metadata["cost_usd"] = _estimate_cost_anthropic(model, usage)

        track_llm_call(
            input=input_text,
            output=output_text,
            prompt=prompt_text,
            model=model,
            metadata=metadata,
        )
    except Exception as exc:
        logger.debug("llm-observe: Anthropic tracking error (non-fatal): %s", exc)


_ANTHROPIC_COSTS_PER_1M = {
    "claude-opus-4-6":   {"input": 5.0,  "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5":  {"input": 1.0,  "output": 5.0},
    "claude-3-opus":     {"input": 15.0, "output": 75.0},
    "claude-3-sonnet":   {"input": 3.0,  "output": 15.0},
    "claude-3-haiku":    {"input": 0.25, "output": 1.25},
}


def _estimate_cost_anthropic(model: str, usage: Any) -> float:
    for key, rates in _ANTHROPIC_COSTS_PER_1M.items():
        if model.startswith(key):
            cost = (
                usage.input_tokens * rates["input"] / 1_000_000
                + usage.output_tokens * rates["output"] / 1_000_000
            )
            return round(cost, 8)
    return 0.0
