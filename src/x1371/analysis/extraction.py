from __future__ import annotations

import json
import shutil
import tarfile
import zipfile
from pathlib import Path

from ..adapters.sevenzip import SevenZipAdapter
from ..config import Settings, ensure_workspace
from ..manifest import append_artifact_store, build_artifact_record
from ..models import ArtifactRecord, EvidenceTier

ARCHIVE_SUFFIXES = {".zip", ".tar", ".gz", ".tgz", ".7z"}


def _safe_output_path(base: Path, member_name: str) -> Path:
    target = (base / member_name).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise ValueError(f"unsafe archive member path: {member_name}")
    return target


def _extract_zip(source: Path, output_dir: Path) -> list[Path]:
    created: list[Path] = []
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = _safe_output_path(output_dir, member.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as handle, target.open("wb") as destination:
                shutil.copyfileobj(handle, destination)
            created.append(target)
    return created


def _extract_tar(source: Path, output_dir: Path) -> list[Path]:
    created: list[Path] = []
    with tarfile.open(source) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            target = _safe_output_path(output_dir, member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as handle, target.open("wb") as destination:
                if handle is None:
                    continue
                shutil.copyfileobj(handle, destination)
            created.append(target)
    return created


def expand_archives(
    artifacts: list[ArtifactRecord],
    settings: Settings,
    *,
    dry_run: bool = False,
) -> dict[str, object]:
    paths = ensure_workspace(settings)
    extracted: list[ArtifactRecord] = []
    failures: list[dict[str, str]] = []
    for artifact in artifacts:
        source = Path(artifact.source_path)
        if source.suffix.lower() not in ARCHIVE_SUFFIXES:
            continue
        output_dir = paths["evidence_derived"] / "expanded" / artifact.artifact_id
        if dry_run:
            continue
        try:
            created_paths: list[Path]
            if zipfile.is_zipfile(source):
                created_paths = _extract_zip(source, output_dir)
                tool = "python-zipfile"
            elif tarfile.is_tarfile(source):
                created_paths = _extract_tar(source, output_dir)
                tool = "python-tarfile"
            else:
                adapter = SevenZipAdapter("7z", settings.tool_paths["sevenzip"])
                result = adapter.extract(source, output_dir)
                if result.returncode not in (0, None):
                    raise RuntimeError(result.stderr or result.error or "7z extraction failed")
                created_paths = [path for path in output_dir.rglob("*") if path.is_file()]
                tool = "7z"
            for created in created_paths:
                extracted.append(
                    build_artifact_record(
                        created,
                        source_root=output_dir,
                        evidence_tier=EvidenceTier.DERIVED,
                        parent_id=artifact.artifact_id,
                        derivation_step="archive_expand",
                        tool=tool,
                        reproducibility={"replayable": True},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            failures.append({"artifact_id": artifact.artifact_id, "error": str(exc)})
    if not dry_run:
        append_artifact_store(settings.workspace, extracted)
        (paths["analysis"] / "archive_expansion.json").write_text(
            json.dumps(
                {
                    "artifacts": [record.to_dict() for record in extracted],
                    "failures": failures,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return {"artifacts": [record.to_dict() for record in extracted], "failures": failures}
