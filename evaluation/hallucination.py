"""
Hallucination heuristic.
Score = 0.0 → no hallucination detected.  Score = 1.0 → likely hallucinating.

v1: pattern-based.
v2 hook: replace `score()` with an LLM judge call.
"""
from __future__ import annotations

import re

# Phrases that signal fabrication or overconfidence without grounding
_OVERCONFIDENCE_PATTERNS = [
    r"\bin \d{4}\b",                      # unsourced dates
    r"\baccording to (studies|research|experts)\b",
    r"\bscientists (say|found|discovered)\b",
    r"\b(always|never|everyone|no one) (does|is|has|will)\b",
    r"\bthe (only|best|worst|first|last) (way|method|solution)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _OVERCONFIDENCE_PATTERNS]


def score(output: str) -> tuple[float, list[str]]:
    """
    Returns (hallucination_score: float, matched_patterns: list[str]).
    """
    hits: list[str] = []
    for pattern in _COMPILED:
        m = pattern.search(output)
        if m:
            hits.append(m.group(0))

    # Each hit adds 0.15, capped at 0.9 (never 1.0 from heuristics alone)
    h_score = min(0.9, len(hits) * 0.15)
    return round(h_score, 3), hits
