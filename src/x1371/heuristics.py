from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from math import log2

from .models import HeuristicLead
from .text_utils import tokenize
from .unicode_analysis import detect_scripts

Analyzer = Callable[[str, str], HeuristicLead]


class HeuristicRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}

    def register(self, name: str) -> Callable[[Analyzer], Analyzer]:
        def decorator(func: Analyzer) -> Analyzer:
            self._analyzers[name] = func
            return func

        return decorator

    def run(self, artifact_id: str, text: str) -> list[HeuristicLead]:
        return [analyzer(artifact_id, text) for analyzer in self._analyzers.values()]


registry = HeuristicRegistry()


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((count / length) * log2(count / length) for count in counts.values())


@registry.register("entropy")
def entropy_lead(artifact_id: str, text: str) -> HeuristicLead:
    entropy = _entropy(text)
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="entropy",
        summary=f"Shannon entropy {entropy:.3f}",
        details={"entropy": entropy, "length": len(text)},
    )


@registry.register("character_distribution")
def character_distribution_lead(artifact_id: str, text: str) -> HeuristicLead:
    common = Counter(text).most_common(10)
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="character_distribution",
        summary="Top character frequencies extracted",
        details={"most_common": common},
    )


@registry.register("ngrams")
def ngram_lead(artifact_id: str, text: str) -> HeuristicLead:
    bigrams = Counter(text[index : index + 2] for index in range(max(0, len(text) - 1))).most_common(10)
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="ngrams",
        summary="Repeated n-grams summarized",
        details={"bigrams": bigrams},
    )


@registry.register("separators")
def separator_lead(artifact_id: str, text: str) -> HeuristicLead:
    separators = Counter(character for character in text if not character.isalnum() and not character.isspace())
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="separators",
        summary="Separator motifs extracted",
        details={"separators": dict(separators)},
    )


@registry.register("chunk_sweep")
def chunk_sweep_lead(artifact_id: str, text: str) -> HeuristicLead:
    lengths = {size: len(text) % size for size in range(2, min(12, max(len(text), 2)))}
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="chunk_sweep",
        summary="Chunk-size remainders computed",
        details={"remainders": lengths},
    )


@registry.register("line_patterns")
def line_pattern_lead(artifact_id: str, text: str) -> HeuristicLead:
    lines = [line for line in text.splitlines() if line]
    lengths = [len(line) for line in lines]
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="line_patterns",
        summary="Line and column structure summarized",
        details={"line_lengths": lengths, "line_count": len(lines)},
    )


@registry.register("encoding_classifier")
def encoding_classifier_lead(artifact_id: str, text: str) -> HeuristicLead:
    tokens = set(text.strip())
    suggestions = []
    if tokens <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r"):
        suggestions.append("base64")
    if tokens <= set("0123456789abcdefABCDEF\n\r "):
        suggestions.append("hex")
    if tokens <= set("01 \n\r"):
        suggestions.append("binary")
    if tokens <= set("01234567 \n\r"):
        suggestions.append("octal")
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="encoding_classifier",
        summary="Likely encodings estimated from character set",
        details={"suggestions": suggestions},
    )


@registry.register("script_mix")
def script_mix_lead(artifact_id: str, text: str) -> HeuristicLead:
    scripts = detect_scripts(text)
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="script_mix",
        summary="Script mix summarized",
        details={"scripts": scripts},
    )


@registry.register("token_profile")
def token_profile_lead(artifact_id: str, text: str) -> HeuristicLead:
    tokens = tokenize(text)
    return HeuristicLead(
        artifact_id=artifact_id,
        analyzer="token_profile",
        summary="Token profile generated",
        details={"token_count": len(tokens), "unique_tokens": len(set(tokens))},
    )
