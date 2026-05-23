from __future__ import annotations

import re
import unicodedata
from collections import Counter

INVISIBLE_CATEGORIES = {"Cf", "Cc"}
BIDI_MARKERS = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
SCRIPT_HINTS = ["LATIN", "CYRILLIC", "GREEK", "HEBREW", "ARABIC", "HIRAGANA", "KATAKANA", "CJK"]

# Characters commonly used as the steganographic alphabet in zero-width encoding schemes
ZERO_WIDTH_STEGO_CHARS: frozenset[str] = frozenset({
    "\u180e",  # Mongolian Vowel Separator
    "\u200b",  # Zero Width Space
    "\u200c",  # Zero Width Non-Joiner
    "\u200d",  # Zero Width Joiner
    "\u202c",  # Pop Directional Formatting
    "\u202d",  # Left-to-Right Override
    "\u202e",  # Right-to-Left Override
    "\u2060",  # Word Joiner
    "\ufeff",  # Zero Width No-Break Space / BOM
})


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


def _decode_stego_bits(bits: str) -> str:
    """Decode a binary string produced by a zero-width stego scheme into readable text."""
    if not bits or len(bits) % 8 != 0:
        return ""
    data = bytes(int(bits[start : start + 8], 2) for start in range(0, len(bits), 8))
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.hex()


def zero_width_stego_extract(text: str) -> dict[str, object]:
    """Extract and attempt to decode a zero-width steganographic payload from *text*.

    The function collects every character that belongs to the zero-width stego
    alphabet, then tries several binary-mapping schemes that are common in
    open-source steganography libraries.  Each successful attempt is included in
    the returned ``attempts`` list.
    """
    payload_chars = [c for c in text if c in ZERO_WIDTH_STEGO_CHARS]
    if not payload_chars:
        return {"found": False, "char_count": 0, "codepoints": [], "unique_chars": [], "attempts": []}

    codepoints = [f"U+{ord(c):04X}" for c in payload_chars]
    unique_chars = sorted({f"U+{ord(c):04X}" for c in payload_chars})
    attempts: list[dict[str, object]] = []

    char_set = sorted(set(payload_chars), key=ord)

    # When exactly two distinct char types are present, treat directly as binary
    if len(char_set) == 2:
        zero_c, one_c = char_set[0], char_set[1]
        bits = "".join("0" if c == zero_c else "1" for c in payload_chars)
        result = _decode_stego_bits(bits)
        if result:
            attempts.append({
                "method": "binary",
                "zero": f"U+{ord(zero_c):04X}",
                "one": f"U+{ord(one_c):04X}",
                "result": result,
            })

    # Common-pair binary attempts regardless of other chars in the stream
    for zero_cp, one_cp in [("\u200c", "\u200d"), ("\u200b", "\u200c")]:
        relevant = [c for c in payload_chars if c in {zero_cp, one_cp}]
        if len(relevant) >= 8 and len(relevant) % 8 == 0:
            bits = "".join("0" if c == zero_cp else "1" for c in relevant)
            result = _decode_stego_bits(bits)
            if result:
                attempts.append({
                    "method": "binary_common_pair",
                    "zero": f"U+{ord(zero_cp):04X}",
                    "one": f"U+{ord(one_cp):04X}",
                    "result": result,
                })

    return {
        "found": True,
        "char_count": len(payload_chars),
        "codepoints": codepoints,
        "unique_chars": unique_chars,
        "attempts": attempts,
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
        "zero_width_stego": zero_width_stego_extract(text),
    }
