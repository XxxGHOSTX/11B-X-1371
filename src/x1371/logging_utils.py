from __future__ import annotations

import json
import logging
from typing import Any


class JsonLikeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(verbose: bool = False) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLikeFormatter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
