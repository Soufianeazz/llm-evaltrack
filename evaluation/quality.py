"""
Heuristic quality scorer.
Score = 1.0 → great.  Score = 0.0 → terrible.

Each check reduces the score and adds a flag.
Designed to be replaced with an LLM judge in v2.
"""
from __future__ import annotations

_MIN_GOOD_LENGTH = 80   # chars
_MAX_REPETITION_RATIO = 0.4


def score(output: str, prompt: str) -> tuple[float, list[str], list[str]]:
    """
    Returns (score: float, flags: list[str], reasons: list[str]).
    reasons feed into score_explanation.
    """
    s = 1.0
    flags: list[str] = []
    reasons: list[str] = []

    stripped = output.strip()

    # 1. Too short
    if len(stripped) < 10:
        s -= 0.5
        flags.append("no_answer")
        reasons.append("output is empty or near-empty")
    elif len(stripped) < _MIN_GOOD_LENGTH:
        s -= 0.25
        flags.append("too_short")
        reasons.append(f"output is only {len(stripped)} chars (threshold {_MIN_GOOD_LENGTH})")

    # 2. Refusal / cop-out patterns
    refusals = ["i cannot", "i can't", "i'm unable", "as an ai", "i don't know"]
    lower = stripped.lower()
    if any(r in lower for r in refusals):
        s -= 0.2
        flags.append("likely_incorrect")
        reasons.append("output contains refusal or uncertainty language")

    # 3. Repetition (poor generation)
    words = lower.split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < (1 - _MAX_REPETITION_RATIO):
            s -= 0.2
            flags.append("likely_incorrect")
            reasons.append(f"high word repetition (unique ratio {unique_ratio:.2f})")

    # 4. Output is just a repeat of the prompt
    if stripped and prompt.strip() and stripped[:100].lower() == prompt.strip()[:100].lower():
        s -= 0.3
        flags.append("likely_incorrect")
        reasons.append("output appears to echo the prompt")

    return max(0.0, round(s, 3)), list(set(flags)), reasons
