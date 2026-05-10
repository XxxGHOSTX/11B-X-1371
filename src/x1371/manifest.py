from __future__ import annotations

import json
import mimetypes
import os
from collections.abc import Iterable
from hashlib import md5, sha1, sha256
from pathlib import Path

from .models import ArtifactRecord, EvidenceTier


def compute_hashes(path: Path, chunk_size: int = 1024 * 1024) -> dict[str, str]:
    sha256_hash = sha256()
    sha1_hash = sha1()
    md5_hash = md5()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            sha256_hash.update(chunk)
            sha1_hash.update(chunk)
            md5_hash.update(chunk)
    return {
        "sha256": sha256_hash.hexdigest(),
        "sha1": sha1_hash.hexdigest(),
        "md5": md5_hash.hexdigest(),
    }


def artifact_class_for(path: Path, mime_type: str | None) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if path.is_dir():
        return "directory", "directory"
    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z"}:
        return "archive", suffix.lstrip(".") or "archive"
    if mime_type and mime_type.startswith("image/"):
        return "image", mime_type.split("/", 1)[1]
    if mime_type and mime_type.startswith("video/"):
        return "video", mime_type.split("/", 1)[1]
    if mime_type and mime_type.startswith("audio/"):
        return "audio", mime_type.split("/", 1)[1]
    if mime_type and mime_type.startswith("text/"):
        return "text", suffix.lstrip(".") or "text"
    return "file", suffix.lstrip(".") or "binary"


def build_artifact_record(
    path: Path,
    *,
    source_root: Path | None = None,
    evidence_tier: EvidenceTier = EvidenceTier.PRIMARY,
    parent_id: str | None = None,
    derivation_step: str | None = None,
    tool: str | None = None,
    transform_parameters: dict[str, object] | None = None,
    suspicion_tags: list[str] | None = None,
    reproducibility: dict[str, object] | None = None,
    determinism: dict[str, object] | None = None,
) -> ArtifactRecord:
    stat = path.stat()
    mime_type, _ = mimetypes.guess_type(path.name)
    artifact_class, artifact_type = artifact_class_for(path, mime_type)
    logical_path = str(path.relative_to(source_root)) if source_root else path.name
    hashes = compute_hashes(path) if path.is_file() else {}
    artifact_id = sha256(f"{logical_path}:{hashes.get('sha256', '')}".encode()).hexdigest()[:16]
    return ArtifactRecord(
        artifact_id=artifact_id,
        source_path=str(path.resolve()),
        logical_path=logical_path,
        artifact_class=artifact_class,
        artifact_type=artifact_type,
        detected_type=mime_type,
        size=stat.st_size,
        hashes=hashes,
        created_at=str(getattr(stat, "st_ctime", "")),
        modified_at=str(getattr(stat, "st_mtime", "")),
        parent_id=parent_id,
        derivation_step=derivation_step,
        tool=tool,
        transform_parameters=dict(transform_parameters or {}),
        reproducibility=dict(reproducibility or {}),
        determinism=dict(determinism or {}),
        suspicion_tags=list(suspicion_tags or []),
        evidence_tier=evidence_tier,
    )


def inventory_inputs(inputs: Iterable[Path]) -> list[Path]:
    discovered: list[Path] = []
    for input_path in inputs:
        if input_path.is_dir():
            discovered.extend(sorted(path for path in input_path.rglob("*") if path.is_file()))
        elif input_path.is_file():
            discovered.append(input_path)
    return discovered


def write_manifest(records: list[ArtifactRecord], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "artifact_count": len(records),
            "tiers": {
                tier.value: sum(1 for record in records if record.evidence_tier == tier)
                for tier in EvidenceTier
            },
        },
        "artifacts": [record.to_dict() for record in records],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return output_path


def load_manifest(path: Path) -> list[ArtifactRecord]:
    payload = json.loads(path.read_text())
    return [ArtifactRecord.from_dict(item) for item in payload.get("artifacts", [])]


def artifact_store_path(workspace: Path) -> Path:
    return workspace / "manifests" / "artifacts.json"


def save_artifact_store(workspace: Path, records: list[ArtifactRecord]) -> Path:
    path = artifact_store_path(workspace)
    return write_manifest(records, path)


def load_artifact_store(workspace: Path) -> list[ArtifactRecord]:
    path = artifact_store_path(workspace)
    if not path.exists():
        return []
    return load_manifest(path)


def append_artifact_store(workspace: Path, new_records: list[ArtifactRecord]) -> list[ArtifactRecord]:
    existing = {record.artifact_id: record for record in load_artifact_store(workspace)}
    for record in new_records:
        existing[record.artifact_id] = record
    merged = list(existing.values())
    save_artifact_store(workspace, merged)
    return merged


def safe_link_or_copy(source: Path, destination: Path, hardlink: bool = True) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    if hardlink:
        try:
            os.link(source, destination)
            return
        except OSError:
            pass
    destination.write_bytes(source.read_bytes())
