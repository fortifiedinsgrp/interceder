"""Tests for the satisfaction signal classifier."""
from __future__ import annotations

from interceder.loops.satisfaction import classify_satisfaction


def test_thanks_is_positive() -> None:
    score = classify_satisfaction("thanks, that's exactly what I needed!")
    assert score > 0.5


def test_correction_is_negative() -> None:
    score = classify_satisfaction("no, that's wrong. I said the OTHER file.")
    assert score < 0.5


def test_neutral_message() -> None:
    score = classify_satisfaction("ok")
    assert 0 <= score <= 1
