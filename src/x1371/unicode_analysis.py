from __future__ import annotations

import re
import unicodedata
from collections import Counter

INVISIBLE_CATEGORIES = {"Cf", "Cc"}
BIDI_MARKERS = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
SCRIPT_HINTS = ["LATIN", "CYRILLIC", "GREEK", "HEBREW", "ARABIC", "HIRAGANA", "KATAKANA", "CJK"]


def codepoint_dump(text: str) -> list[dict[str, object]]:
    return [
        {
            "character": character,
            "codepoint": f"U+{ord(character):04X}",
            "name": unicodedata.name(character, "UNKNOWN"),
            "category": unicodedata.category(character),
        }
        for character in text
    ]


def normalization_differences(text: str) -> dict[str, str]:
    return {form: unicodedata.normalize(form, text) for form in ("NFC", "NFD", "NFKC", "NFKD")}


def invisible_characters(text: str) -> list[dict[str, str]]:
    findings = []
    for character in text:
        category = unicodedata.category(character)
        if category in INVISIBLE_CATEGORIES and character not in {"\n", "\t", "\r"}:
            findings.append({"character": character, "codepoint": f"U+{ord(character):04X}"})
    return findings


def bidi_markers(text: str) -> list[dict[str, str]]:
    markers = []
    for character in text:
        bidi = unicodedata.bidirectional(character)
        if bidi in BIDI_MARKERS:
            markers.append({"character": character, "codepoint": f"U+{ord(character):04X}", "bidi": bidi})
    return markers


def detect_scripts(text: str) -> dict[str, int]:
    scripts: Counter[str] = Counter()
    for character in text:
        if not character.isalpha():
            continue
        name = unicodedata.name(character, "")
        for script in SCRIPT_HINTS:
            if script in name:
                scripts[script] += 1
                break
        else:
            scripts["OTHER"] += 1
    return dict(scripts)


def homoglyph_suspicion(text: str) -> list[str]:
    scripts = detect_scripts(text)
    suspicious: list[str] = []
    if len([script for script, count in scripts.items() if count > 0]) > 1:
        suspicious.append("mixed-script text may contain homoglyphs")
    if re.search(r"[A-Za-z].*[А-Яа-я]", text) or re.search(r"[А-Яа-я].*[A-Za-z]", text):
        suspicious.append("Latin and Cyrillic characters appear together")
    return suspicious


def whitespace_summary(text: str) -> dict[str, int]:
    return {
        "spaces": text.count(" "),
        "tabs": text.count("\t"),
        "newlines": text.count("\n"),
        "double_spaces": text.count("  "),
    }


def repeated_motifs(text: str, sizes: tuple[int, ...] = (2, 3, 4)) -> dict[str, int]:
    motifs: Counter[str] = Counter()
    for size in sizes:
        for index in range(0, max(0, len(text) - size + 1)):
            motif = text[index : index + size]
            motifs[motif] += 1
    return {motif: count for motif, count in motifs.items() if count > 1}


def delimiter_summary(text: str) -> dict[str, int]:
    delimiters = [character for character in text if character in ",.;:|/-_[]{}()<>"]
    return dict(Counter(delimiters))


def chunk_patterns(text: str) -> dict[str, object]:
    lines = [line for line in text.splitlines() if line]
    lengths = [len(line) for line in lines]
    return {
        "line_lengths": lengths,
        "unique_lengths": sorted(set(lengths)),
        "common_words": dict(Counter(re.findall(r"\w+", text.lower())).most_common(10)),
    }


def analyze_unicode(text: str) -> dict[str, object]:
    return {
        "codepoints": codepoint_dump(text),
        "normalizations": normalization_differences(text),
        "invisible_characters": invisible_characters(text),
        "bidi_markers": bidi_markers(text),
        "scripts": detect_scripts(text),
        "homoglyph_suspicion": homoglyph_suspicion(text),
        "whitespace": whitespace_summary(text),
        "motifs": repeated_motifs(text),
        "delimiters": delimiter_summary(text),
        "chunk_patterns": chunk_patterns(text),
    }
