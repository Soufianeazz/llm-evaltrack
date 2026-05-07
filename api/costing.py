from __future__ import annotations

from typing import Any


# USD per 1M tokens (input, output)
# Keep this table small and explicit; extend as needed.
_MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-5-haiku": (0.80, 4.00),
}


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        n = int(float(value))
        return n if n >= 0 else None
    except Exception:
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def normalize_model(model: str | None) -> str | None:
    if not model:
        return None
    m = model.strip().lower()
    if m.startswith("gpt-4o-mini"):
        return "gpt-4o-mini"
    if m.startswith("gpt-4o"):
        return "gpt-4o"
    if m.startswith("gpt-4.1-mini"):
        return "gpt-4.1-mini"
    if m.startswith("claude-3-5-haiku"):
        return "claude-3-5-haiku"
    if m.startswith("claude-3-haiku"):
        return "claude-3-haiku"
    return m


def estimate_tokens_from_text(text: str | None) -> int:
    if not text:
        return 0
    # Simple, deterministic approximation for missing usage metadata.
    return max(1, len(text) // 4)


def extract_token_counts(
    metadata: dict[str, Any] | None,
    input_text: str | None = None,
    output_text: str | None = None,
) -> tuple[int, int]:
    meta = metadata or {}
    in_tokens = _to_int(meta.get("input_tokens"))
    out_tokens = _to_int(meta.get("output_tokens"))
    if in_tokens is None:
        in_tokens = estimate_tokens_from_text(input_text)
    if out_tokens is None:
        out_tokens = estimate_tokens_from_text(output_text)
    return in_tokens, out_tokens


def compute_cost_from_tokens(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    key = normalize_model(model)
    if not key:
        return None
    pricing = _MODEL_PRICING_PER_1M.get(key)
    if not pricing:
        return None
    in_price, out_price = pricing
    cost = (input_tokens / 1_000_000.0) * in_price + (output_tokens / 1_000_000.0) * out_price
    return round(cost, 8)


def compute_request_cost(
    model: str | None,
    metadata: dict[str, Any] | None,
    input_text: str | None = None,
    output_text: str | None = None,
) -> float:
    in_tokens, out_tokens = extract_token_counts(metadata, input_text=input_text, output_text=output_text)
    computed = compute_cost_from_tokens(model, in_tokens, out_tokens)
    if computed is not None:
        return computed
    fallback = _to_float((metadata or {}).get("cost_usd"))
    return round(fallback, 8) if fallback is not None else 0.0

