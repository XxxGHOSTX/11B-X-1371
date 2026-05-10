from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".htm",
    ".yml",
    ".yaml",
    ".ini",
    ".toml",
    ".log",
}


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFKC", normalized)


def decode_bytes(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            return normalize_text(payload.decode(encoding))
        except UnicodeDecodeError:
            continue
    return normalize_text(payload.decode("utf-8", errors="replace"))


def read_text_file(path: Path) -> str:
    return decode_bytes(path.read_bytes())


def is_probably_text(path: Path, detected_type: str | None = None) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return bool(detected_type and detected_type.startswith("text/"))


def tokenize(text: str) -> list[str]:
    return re.findall(r"[\w']+", normalize_text(text).lower())


def repeated_tokens(text: str, minimum_count: int = 2) -> dict[str, int]:
    counts = Counter(tokenize(text))
    return {token: count for token, count in counts.items() if count >= minimum_count}
