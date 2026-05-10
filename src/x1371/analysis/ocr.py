from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..adapters.tesseract import TesseractAdapter
from ..config import Settings, ensure_workspace
from ..manifest import append_artifact_store, build_artifact_record
from ..models import ArtifactRecord, EvidenceTier
from ..text_utils import normalize_text
from .symbol_analysis import extract_symbol_stream

OCRPass = Callable[[ArtifactRecord, Settings], list[ArtifactRecord]]


class OCRRegistry:
    def __init__(self) -> None:
        self._passes: dict[str, OCRPass] = {}

    def register(self, name: str) -> Callable[[OCRPass], OCRPass]:
        def decorator(func: OCRPass) -> OCRPass:
            self._passes[name] = func
            return func

        return decorator

    def run(self, artifacts: list[ArtifactRecord], settings: Settings) -> dict[str, list[ArtifactRecord]]:
        return {name: handler(artifact, settings) for name, handler in self._passes.items() for artifact in artifacts}


registry = OCRRegistry()


@registry.register("tesseract")
def tesseract_pass(artifact: ArtifactRecord, settings: Settings) -> list[ArtifactRecord]:
    adapter = TesseractAdapter("tesseract", settings.tool_paths["tesseract"])
    if artifact.artifact_class != "image" or not adapter.available():
        return []
    paths = ensure_workspace(settings)
    output_dir = paths["analysis"] / "ocr" / artifact.artifact_id
    derived: list[ArtifactRecord] = []
    for config in settings.ocr_passes:
        output_base = output_dir / config["name"]
        result = adapter.ocr(
            Path(artifact.source_path),
            output_base,
            lang=str(config.get("lang", "eng")),
            psm=int(config.get("psm", 6)),
            oem=int(config.get("oem", 1)),
        )
        txt_path = output_base.with_suffix(".txt")
        if result.returncode not in (0, None) or not txt_path.exists():
            continue
        normalized_path = output_dir / f"{config['name']}.normalized.txt"
        normalized_text = normalize_text(txt_path.read_text())
        normalized_path.write_text(normalized_text)
        symbol_path = output_dir / f"{config['name']}.symbols.json"
        symbol_path.write_text(json.dumps(extract_symbol_stream(normalized_text), indent=2, ensure_ascii=False))
        derived.append(
            build_artifact_record(
                normalized_path,
                source_root=output_dir,
                evidence_tier=EvidenceTier.DERIVED,
                parent_id=artifact.artifact_id,
                derivation_step="ocr",
                tool="tesseract",
                transform_parameters=config,
                reproducibility={"replayable": True},
            )
        )
    return derived


def run_ocr(artifacts: list[ArtifactRecord], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    ensure_workspace(settings)
    derived: list[ArtifactRecord] = []
    for artifact in artifacts:
        derived.extend(tesseract_pass(artifact, settings))
    if not dry_run:
        append_artifact_store(settings.workspace, derived)
    return {"artifacts": [record.to_dict() for record in derived]}
