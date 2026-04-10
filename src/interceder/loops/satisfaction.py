"""Satisfaction signal classifier for L1 user-model loop.

Classifies user follow-up messages as positive/negative satisfaction signals.
In production, this uses Haiku for cheap classification. For Phase 12,
a keyword-based heuristic provides the baseline.
"""
from __future__ import annotations

import re

# Positive signals
_POSITIVE = re.compile(
    r"\b(thanks|thank you|perfect|exactly|great|awesome|nice|correct|yes|right)\b",
    re.IGNORECASE,
)

# Negative signals
_NEGATIVE = re.compile(
    r"\b(wrong|no|incorrect|not what|stop|don't|fix|undo|revert|bad)\b",
    re.IGNORECASE,
)


def classify_satisfaction(message: str) -> float:
    """Return a satisfaction score from 0.0 (dissatisfied) to 1.0 (satisfied).

    Phase 12: keyword heuristic. Real implementation uses Haiku classifier.
    """
    pos_count = len(_POSITIVE.findall(message))
    neg_count = len(_NEGATIVE.findall(message))
    total = pos_count + neg_count

    if total == 0:
        return 0.5  # neutral

    return pos_count / total
