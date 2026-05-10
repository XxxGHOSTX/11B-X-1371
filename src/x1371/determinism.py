from __future__ import annotations

import json
from collections.abc import Callable
from hashlib import sha256
from typing import Any

from .models import DeterminismRecord


def validate_determinism(step_name: str, runner: Callable[[], Any], *, iterations: int = 2) -> DeterminismRecord:
    serialized: list[str] = []
    values: list[Any] = []
    for _ in range(iterations):
        value = runner()
        values.append(value)
        serialized.append(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))
    digest = sha256("||".join(serialized).encode()).hexdigest()
    stable = len(set(serialized)) == 1
    mismatches: list[dict[str, Any]] = []
    if not stable:
        baseline = serialized[0]
        for index, item in enumerate(serialized[1:], start=1):
            if item != baseline:
                mismatches.append({"iteration": index, "value": values[index]})
    causes = [] if stable else ["non-deterministic tool output", "timestamp or filesystem ordering variance"]
    return DeterminismRecord(
        step_name=step_name,
        stable=stable,
        digest=digest,
        iterations=iterations,
        mismatches=mismatches,
        likely_causes=causes,
    )
