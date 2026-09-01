"""Shared citation-grounding check: does a citation trace back to retrieved text?

Used both by the agent's post-hoc verification step and by the evaluation
metrics, so the two always agree.
"""

from __future__ import annotations

import re

GROUNDING_THRESHOLD = 0.6

_STOPWORDS = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "is",
        "was",
        "as",
        "by",
        "with",
        "that",
        "this",
        "it",
        "its",
        "from",
        "into",
        "then",
        "than",
        "due",
        "caused",
        "cause",
        "root",
        "error",
        "errors",
        "issue",
        "service",
        "during",
        "over",
        "under",
        "starting",
        "began",
        "begin",
        "around",
        "approximately",
        "about",
    ]
)


def content_words(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9._:/-]*", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _STOPWORDS]


def grounding_score(citation: str, sources: list[str]) -> float:
    """Best fraction of the citation's content words found in any single source."""
    words = content_words(citation)
    if not words:
        return 0.0
    best = 0.0
    for source in sources:
        hay = set(content_words(source))
        best = max(best, sum(w in hay for w in words) / len(words))
    return best


def is_grounded(citation: str, sources: list[str], threshold: float = GROUNDING_THRESHOLD) -> bool:
    return grounding_score(citation, sources) >= threshold
