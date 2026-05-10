from __future__ import annotations

import unicodedata
from collections import Counter

NON_WORD = {"Po", "Ps", "Pe", "Sm", "Sc", "Sk", "So"}


def extract_symbol_stream(text: str) -> dict[str, object]:
    symbols = [character for character in text if not character.isalnum() and not character.isspace()]
    categories = Counter(unicodedata.category(character) for character in symbols)
    names = {character: unicodedata.name(character, "UNKNOWN") for character in set(symbols)}
    return {
        "symbol_count": len(symbols),
        "symbols": dict(Counter(symbols)),
        "categories": dict(categories),
        "names": names,
    }
