"""
Evaluation engine — orchestrates quality + hallucination scorers.
Single entry point: evaluate_request().

Evaluation strategy (in priority order):
  1. LLM judge (Claude) — if ANTHROPIC_API_KEY is set, sampling gate passes, and daily cap not hit
  2. Heuristics         — fallback when API key is missing, sampling skips, cap hit, or judge call fails
"""
from __future__ import annotations

import logging
import os
import random
import threading
from datetime import datetime, timezone

from evaluation import quality, hallucination

logger = logging.getLogger(__name__)

_judge_state_lock = threading.Lock()
_judge_calls_today = 0
_judge_calls_date: str | None = None


def _judge_allowed() -> bool:
    """Cost guardrail: respect JUDGE_DAILY_CAP and JUDGE_SAMPLE_RATE."""
    global _judge_calls_today, _judge_calls_date

    try:
        sample_rate = float(os.environ.get("JUDGE_SAMPLE_RATE", "0.1"))
    except ValueError:
        sample_rate = 0.1
    if random.random() >= sample_rate:
        return False

    try:
        daily_cap = int(os.environ.get("JUDGE_DAILY_CAP", "500"))
    except ValueError:
        daily_cap = 500

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _judge_state_lock:
        if _judge_calls_date != today:
            _judge_calls_date = today
            _judge_calls_today = 0
        if _judge_calls_today >= daily_cap:
            logger.warning("Judge daily cap (%d) reached, using heuristics", daily_cap)
            return False
        _judge_calls_today += 1
    return True


def _heuristic_evaluate(input_: str, output: str, prompt: str) -> dict:
    q_score, q_flags, q_reasons = quality.score(output, prompt)
    h_score, h_matches = hallucination.score(output)

    flags = list(q_flags)
    if h_score >= 0.3:
        flags.append("possible_hallucination")

    parts: list[str] = []
    if q_reasons:
        parts.append("Quality issues: " + "; ".join(q_reasons))
    if h_matches:
        parts.append("Hallucination signals: " + ", ".join(f'"{m}"' for m in h_matches))
    explanation = " | ".join(parts) if parts else "No issues detected"

    return {
        "quality_score": q_score,
        "hallucination_score": h_score,
        "flags": flags,
        "explanation": f"[heuristic] {explanation}",
    }


def evaluate_request(input_: str, output: str, prompt: str) -> dict:
    """
    Evaluate an LLM response.
    Uses Claude as judge when ANTHROPIC_API_KEY is available, otherwise heuristics.
    """
    has_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("anthropic-api-key")
    if has_key and _judge_allowed():
        try:
            from evaluation import llm_judge
            result = llm_judge.evaluate(input_, output, prompt)
            logger.info("LLM judge evaluation complete (quality=%.2f)", result["quality_score"])
            return result
        except Exception as exc:
            logger.warning("LLM judge failed (%s), falling back to heuristics", exc)

    return _heuristic_evaluate(input_, output, prompt)
