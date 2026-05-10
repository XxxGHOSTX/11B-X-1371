from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import Settings, ensure_workspace
from ..heuristics import registry as heuristic_registry
from ..text_utils import is_probably_text, read_text_file
from ..unicode_analysis import analyze_unicode
from .symbol_analysis import extract_symbol_stream


def analyze_texts(text_map: dict[str, str], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    paths = ensure_workspace(settings)
    results: dict[str, Any] = {}
    for artifact_id, text in text_map.items():
        results[artifact_id] = {
            "unicode": analyze_unicode(text),
            "heuristics": [lead.to_dict() for lead in heuristic_registry.run(artifact_id, text)],
            "symbols": extract_symbol_stream(text),
        }
    if not dry_run:
        (paths["analysis"] / "text_analysis.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return results


def collect_text_artifacts(artifacts: list[object]) -> dict[str, str]:
    text_map: dict[str, str] = {}
    for artifact in artifacts:
        path = Path(artifact.source_path)
        if path.exists() and path.is_file() and (artifact.artifact_class == "text" or is_probably_text(path, artifact.detected_type)):
            text_map[artifact.artifact_id] = read_text_file(path)
    return text_map
