from __future__ import annotations

import string
from base64 import a85decode, b16decode, b32decode, b64decode, b85decode
from binascii import Error as BinasciiError
from collections.abc import Iterable
from dataclasses import dataclass

from ..unicode_analysis import ZERO_WIDTH_STEGO_CHARS
from .scoring import structuredness


@dataclass(slots=True)
class TransformResult:
    output: str
    parameters: dict[str, object]
    validation_notes: list[str]
    structuredness: dict[str, float]


def _result(output: str, parameters: dict[str, object] | None = None, note: str | None = None) -> TransformResult:
    notes = [note] if note else []
    return TransformResult(output=output, parameters=parameters or {}, validation_notes=notes, structuredness=structuredness(output))


def reverse_transform(text: str) -> Iterable[TransformResult]:
    yield _result(text[::-1])


def rot_transform(text: str) -> Iterable[TransformResult]:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    for shift in range(1, 26):
        transformed: list[str] = []
        for character in text:
            if character in lower:
                transformed.append(lower[(lower.index(character) + shift) % 26])
            elif character in upper:
                transformed.append(upper[(upper.index(character) + shift) % 26])
            else:
                transformed.append(character)
        yield _result("".join(transformed), {"shift": shift})


def atbash_transform(text: str) -> Iterable[TransformResult]:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    table = str.maketrans(lower + upper, lower[::-1] + upper[::-1])
    yield _result(text.translate(table))


def _bytes_to_text(payload: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.hex()


def _bits_to_bytes(bits: str) -> bytes:
    """Pack a binary string (multiples of 8 chars) into bytes."""
    return bytes(int(bits[start : start + 8], 2) for start in range(0, len(bits), 8))


def base_transform(text: str) -> Iterable[TransformResult]:
    compact = "".join(text.split())
    decoders = {
        "base16": lambda value: b16decode(value.upper(), casefold=True),
        "base32": lambda value: b32decode(value.upper()),
        "base64": lambda value: b64decode(value, validate=True),
        "base85": b85decode,
        "ascii85": a85decode,
    }
    for name, decoder in decoders.items():
        try:
            decoded = decoder(compact.encode())
        except (BinasciiError, ValueError):
            continue
        yield _result(_bytes_to_text(decoded), {"decoder": name})


def hex_transform(text: str) -> Iterable[TransformResult]:
    compact = "".join(character for character in text if character in string.hexdigits)
    if compact and len(compact) % 2 == 0:
        yield _result(_bytes_to_text(bytes.fromhex(compact)), {"mode": "hex"})


def binary_transform(text: str) -> Iterable[TransformResult]:
    compact = "".join(character for character in text if character in "01")
    if compact and len(compact) % 8 == 0:
        data = bytes(int(compact[index : index + 8], 2) for index in range(0, len(compact), 8))
        yield _result(_bytes_to_text(data), {"mode": "binary"})


def octal_decimal_transform(text: str) -> Iterable[TransformResult]:
    parts = [chunk for chunk in text.replace(",", " ").split() if chunk]
    if not parts:
        return
    if all(part.isdigit() and int(part) < 256 for part in parts):
        decoded = bytes(int(part) for part in parts)
        yield _result(_bytes_to_text(decoded), {"mode": "decimal-bytes"})
    if all(set(part) <= set("01234567") for part in parts):
        decoded = bytes(int(part, 8) for part in parts if int(part, 8) < 256)
        yield _result(_bytes_to_text(decoded), {"mode": "octal-bytes"})


def grid_transform(text: str) -> Iterable[TransformResult]:
    lines = [line for line in text.splitlines() if line]
    if len(lines) < 2:
        return
    width = min(len(line) for line in lines)
    clipped = [line[:width] for line in lines]
    columns = ["".join(row[index] for row in clipped) for index in range(width)]
    yield _result("\n".join(columns), {"mode": "columns"})
    yield _result("".join(columns), {"mode": "columns_joined"})


def mirrored_transform(text: str) -> Iterable[TransformResult]:
    mapping = str.maketrans("()[]{}<>/\\", ")(][}{><\\/")
    yield _result(text.translate(mapping)[::-1], {"mode": "mirrored"})


def upside_down_transform(text: str) -> Iterable[TransformResult]:
    mapping = str.maketrans({
        "a": "ɐ",
        "b": "q",
        "c": "ɔ",
        "d": "p",
        "e": "ǝ",
        "f": "ɟ",
        "g": "ƃ",
        "h": "ɥ",
        "i": "ᴉ",
        "j": "ɾ",
        "k": "ʞ",
        "l": "ן",
        "m": "ɯ",
        "n": "u",
        "o": "o",
        "p": "d",
        "q": "b",
        "r": "ɹ",
        "s": "s",
        "t": "ʇ",
        "u": "n",
        "v": "ʌ",
        "w": "ʍ",
        "x": "x",
        "y": "ʎ",
        "z": "z",
    })
    yield _result(text.lower().translate(mapping)[::-1], {"mode": "upside_down"})


def transposition_helpers(text: str) -> Iterable[TransformResult]:
    compact = "".join(text.split())
    evens = compact[0::2]
    odds = compact[1::2]
    for size in range(2, min(7, len(compact) + 1)):
        chunks = [compact[index : index + size] for index in range(0, len(compact), size)]
        yield _result("".join(chunk[::-1] for chunk in chunks), {"mode": "chunk_reverse", "size": size})
        yield _result(evens + odds, {"mode": "even_odd", "size": size})


def unicode_stego_transform(text: str) -> Iterable[TransformResult]:
    """Extract and binary-decode a zero-width steganographic payload embedded in *text*.

    Characters from the common stego alphabet (zero-width spaces, joiners,
    directional marks, etc.) are collected and mapped to bits.  The two most
    prevalent schemes tried are:

    * When exactly two distinct stego chars are present the lower codepoint maps
      to ``0`` and the higher to ``1``.
    * The ZWNJ (U+200C) / ZWJ (U+200D) and ZWS (U+200B) / ZWNJ (U+200C) pairs
      used by popular open-source libraries are always attempted.
    """
    payload_chars = [c for c in text if c in ZERO_WIDTH_STEGO_CHARS]
    if not payload_chars:
        return

    char_set = sorted(set(payload_chars), key=ord)

    if len(char_set) == 2:
        zero_c, one_c = char_set[0], char_set[1]
        bits = "".join("0" if c == zero_c else "1" for c in payload_chars)
        if bits and len(bits) % 8 == 0:
            yield _result(
                _bytes_to_text(_bits_to_bytes(bits)),
                {"mode": "binary", "zero": f"U+{ord(zero_c):04X}", "one": f"U+{ord(one_c):04X}"},
            )

    for zero_cp, one_cp in [("\u200c", "\u200d"), ("\u200b", "\u200c")]:
        relevant = [c for c in payload_chars if c in {zero_cp, one_cp}]
        if len(relevant) >= 8 and len(relevant) % 8 == 0:
            bits = "".join("0" if c == zero_cp else "1" for c in relevant)
            yield _result(
                _bytes_to_text(_bits_to_bytes(bits)),
                {
                    "mode": "binary_common_pair",
                    "zero": f"U+{ord(zero_cp):04X}",
                    "one": f"U+{ord(one_cp):04X}",
                },
            )
