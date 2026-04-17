"""
Evaluation engine — orchestrates quality + hallucination scorers.
Single entry point: evaluate_request().

Evaluation strategy (in priority order):
  1. LLM judge (Claude) — if ANTHROPIC_API_KEY is set
  2. Heuristics         — fallback when API key is missing or call fails
"""
from __future__ import annotations

import logging
import os

from evaluation import quality, hallucination

logger = logging.getLogger(__name__)


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
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("anthropic-api-key"):
        try:
            from evaluation import llm_judge
            result = llm_judge.evaluate(input_, output, prompt)
            logger.info("LLM judge evaluation complete (quality=%.2f)", result["quality_score"])
            return result
        except Exception as exc:
            logger.warning("LLM judge failed (%s), falling back to heuristics", exc)

    return _heuristic_evaluate(input_, output, prompt)
