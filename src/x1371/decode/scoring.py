from __future__ import annotations

import string
from collections import Counter
from math import log2


def entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((count / total) * log2(count / total) for count in counts.values())


def structuredness(text: str) -> dict[str, float]:
    if not text:
        return {"printable_ratio": 0.0, "ascii_ratio": 0.0, "entropy": 0.0, "word_ratio": 0.0}
    printable = sum(character in string.printable for character in text)
    ascii_count = sum(ord(character) < 128 for character in text)
    words = sum(character.isalpha() for character in text)
    length = len(text)
    return {
        "printable_ratio": printable / length,
        "ascii_ratio": ascii_count / length,
        "entropy": entropy(text),
        "word_ratio": words / length,
    }


def unexplained_residue(text: str) -> str:
    return "".join(character for character in text if character not in string.printable or character == "�")


def score_output(
    text: str,
    *,
    residue: str = "",
    deterministic: bool = True,
    reproducible: bool = True,
    cross_source_support: int = 0,
    external_claim_dependency: bool = False,
    stable: bool = True,
) -> float:
    metrics = structuredness(text)
    score = 0.0
    score += metrics["printable_ratio"] * 30
    score += metrics["ascii_ratio"] * 15
    score += metrics["word_ratio"] * 20
    score += max(0.0, 10 - abs(metrics["entropy"] - 4.2) * 2)
    score += cross_source_support * 8
    score -= len(residue) * 1.5
    if deterministic:
        score += 10
    if reproducible:
        score += 5
    if stable:
        score += 5
    if external_claim_dependency:
        score -= 25
    return round(score, 3)
