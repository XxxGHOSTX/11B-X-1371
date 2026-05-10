from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..adapters.binwalk import BinwalkAdapter
from ..adapters.exiftool import ExifToolAdapter
from ..adapters.ffmpeg import FFmpegAdapter
from ..adapters.file_cmd import FileCommandAdapter
from ..adapters.strings_cmd import StringsAdapter
from ..config import Settings, ensure_workspace
from ..models import ArtifactRecord
from ..text_utils import is_probably_text, read_text_file


@dataclass(slots=True)
class MetadataOutcome:
    name: str
    normalized: dict[str, Any]
    raw: str | dict[str, Any]


Extractor = Callable[[ArtifactRecord, Settings], MetadataOutcome]


class MetadataExtractorRegistry:
    def __init__(self) -> None:
        self._extractors: dict[str, Extractor] = {}

    def register(self, name: str) -> Callable[[Extractor], Extractor]:
        def decorator(func: Extractor) -> Extractor:
            self._extractors[name] = func
            return func

        return decorator

    def items(self) -> list[tuple[str, Extractor]]:
        return list(self._extractors.items())


registry = MetadataExtractorRegistry()


@registry.register("stat")
def stat_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    del settings
    path = Path(artifact.source_path)
    stat = path.stat()
    return MetadataOutcome(
        name="stat",
        normalized={
            "size": stat.st_size,
            "created_at": artifact.created_at,
            "modified_at": artifact.modified_at,
            "suffix": path.suffix.lower(),
        },
        raw={"st_mode": stat.st_mode, "st_size": stat.st_size},
    )


@registry.register("file")
def file_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    adapter = FileCommandAdapter("file", settings.tool_paths["file"])
    result = adapter.identify(Path(artifact.source_path))
    return MetadataOutcome(
        name="file",
        normalized={"detected_type": result.stdout.strip() or artifact.detected_type},
        raw=result.to_dict(),
    )


@registry.register("exiftool")
def exif_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    adapter = ExifToolAdapter("exiftool", settings.tool_paths["exiftool"])
    result = adapter.metadata(Path(artifact.source_path))
    parsed: Any
    try:
        parsed = json.loads(result.stdout) if result.stdout else []
    except json.JSONDecodeError:
        parsed = []
    return MetadataOutcome(
        name="exiftool",
        normalized={"available": result.available, "records": parsed if isinstance(parsed, list) else [parsed]},
        raw=result.to_dict(),
    )


@registry.register("ffprobe")
def ffprobe_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    adapter = FFmpegAdapter(settings.tool_paths["ffmpeg"], settings.tool_paths["ffprobe"])
    result = adapter.probe(Path(artifact.source_path))
    parsed: dict[str, Any] = {}
    if result.stdout:
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = {}
    return MetadataOutcome(name="ffprobe", normalized=parsed, raw=result.to_dict())


@registry.register("strings")
def strings_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    path = Path(artifact.source_path)
    if is_probably_text(path, artifact.detected_type):
        preview = read_text_file(path)[:1000]
        return MetadataOutcome(name="strings", normalized={"preview": preview}, raw=preview)
    adapter = StringsAdapter("strings", settings.tool_paths["strings"])
    result = adapter.extract(path)
    return MetadataOutcome(name="strings", normalized={"preview": result.stdout[:1000]}, raw=result.to_dict())


@registry.register("binwalk")
def binwalk_extractor(artifact: ArtifactRecord, settings: Settings) -> MetadataOutcome:
    adapter = BinwalkAdapter("binwalk", settings.tool_paths["binwalk"])
    result = adapter.scan(Path(artifact.source_path))
    parsed: Any = []
    if result.stdout:
        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            parsed = []
    return MetadataOutcome(name="binwalk", normalized={"results": parsed}, raw=result.to_dict())


def extract_metadata(artifacts: list[ArtifactRecord], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    paths = ensure_workspace(settings)
    normalized_dir = paths["metadata"] / "normalized"
    raw_dir = paths["metadata"] / "raw"
    summary: dict[str, Any] = {}
    for artifact in artifacts:
        artifact_summary: dict[str, Any] = {
            "artifact_id": artifact.artifact_id,
            "source_path": artifact.source_path,
            "extractors": {},
        }
        for name, extractor in registry.items():
            outcome = extractor(artifact, settings)
            artifact_summary["extractors"][name] = outcome.normalized
            if not dry_run:
                artifact_raw_dir = raw_dir / artifact.artifact_id
                artifact_raw_dir.mkdir(parents=True, exist_ok=True)
                suffix = "json" if isinstance(outcome.raw, dict) else "txt"
                raw_path = artifact_raw_dir / f"{name}.{suffix}"
                raw_payload = outcome.raw if isinstance(outcome.raw, str) else json.dumps(outcome.raw, indent=2, ensure_ascii=False)
                raw_path.write_text(raw_payload)
        summary[artifact.artifact_id] = artifact_summary
        if not dry_run:
            normalized_dir.mkdir(parents=True, exist_ok=True)
            (normalized_dir / f"{artifact.artifact_id}.json").write_text(
                json.dumps(artifact_summary, indent=2, ensure_ascii=False)
            )
    if not dry_run:
        (paths["metadata"] / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
