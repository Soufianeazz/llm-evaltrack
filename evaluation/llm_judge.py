"""
LLM-based evaluator using Claude as a judge.
Replaces heuristic scorers with a real model call.

Requires ANTHROPIC_API_KEY in the environment.
Falls back to heuristics automatically if the API key is missing or the call fails.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

_JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-4-5-20251001")

_SYSTEM_PROMPT = """You are an expert LLM output evaluator.
Your job is to assess the quality of an AI assistant's response.
Always respond with valid JSON only — no prose, no markdown, just the JSON object."""

_USER_TEMPLATE = """Evaluate this AI response:

PROMPT (instruction given to the AI):
{prompt}

USER INPUT:
{input}

AI OUTPUT:
{output}

Return a JSON object with exactly these fields:
{{
  "quality_score": <float 0.0-1.0>,
  "hallucination_score": <float 0.0-1.0>,
  "flags": <list of strings from: "too_short", "no_answer", "likely_incorrect", "possible_hallucination">,
  "explanation": <one sentence explaining the scores>
}}

Scoring guide:
- quality_score: 1.0 = perfect answer, 0.0 = completely wrong/empty/irrelevant
- hallucination_score: 0.0 = fully grounded, 1.0 = clearly fabricated facts
- flags: add relevant flags only when the issue is clearly present"""


def evaluate(input_: str, output: str, prompt: str) -> dict:
    """
    Call Claude to evaluate the LLM response.
    Returns the same dict shape as the heuristic engine.
    Raises RuntimeError if the API call fails (caller should fall back to heuristics).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("anthropic-api-key")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    import anthropic  # lazy import — only needed when this evaluator is active

    client = anthropic.Anthropic(api_key=api_key)

    user_message = _USER_TEMPLATE.format(
        prompt=prompt[:500],
        input=input_[:500],
        output=output[:1000],
    )

    response = client.messages.create(
        model=_JUDGE_MODEL,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = next(
        (block.text for block in response.content if block.type == "text"),
        None,
    )
    if not text:
        raise RuntimeError("No text block in judge response")

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    result = json.loads(text)

    return {
        "quality_score": float(result.get("quality_score", 0.5)),
        "hallucination_score": float(result.get("hallucination_score", 0.0)),
        "flags": result.get("flags", []),
        "explanation": result.get("explanation", ""),
    }
