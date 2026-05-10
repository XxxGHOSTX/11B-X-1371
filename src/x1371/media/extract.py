from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..adapters.ffmpeg import FFmpegAdapter
from ..config import Settings, ensure_workspace
from ..manifest import append_artifact_store, build_artifact_record, compute_hashes
from ..models import ArtifactRecord, EvidenceTier

VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def extract_media(artifacts: list[ArtifactRecord], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    paths = ensure_workspace(settings)
    adapter = FFmpegAdapter(settings.tool_paths["ffmpeg"], settings.tool_paths["ffprobe"])
    derived: list[ArtifactRecord] = []
    summary: dict[str, Any] = {"processed": [], "skipped": []}
    for artifact in artifacts:
        source = Path(artifact.source_path)
        if source.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        if not adapter.available():
            summary["skipped"].append({"artifact_id": artifact.artifact_id, "reason": "ffmpeg/ffprobe not installed"})
            continue
        out_dir = paths["evidence_derived"] / "media" / artifact.artifact_id
        frames_pattern = out_dir / "frames" / "%06d.png"
        audio_path = out_dir / "audio" / f"{source.stem}.mka"
        if dry_run:
            continue
        probe_result = adapter.probe(source)
        frame_probe = adapter.probe_frames(source)
        adapter.extract_frames(source, frames_pattern)
        adapter.extract_audio(source, audio_path)
        frame_records = []
        for frame in sorted((out_dir / "frames").glob("*.png")):
            record = build_artifact_record(
                frame,
                source_root=out_dir,
                evidence_tier=EvidenceTier.DERIVED,
                parent_id=artifact.artifact_id,
                derivation_step="media_extract_frames",
                tool="ffmpeg",
                reproducibility={"replayable": True},
            )
            if settings.compute_frame_hashes:
                record.hashes = compute_hashes(frame)
            derived.append(record)
            frame_records.append(record.to_dict())
        if audio_path.exists():
            derived.append(
                build_artifact_record(
                    audio_path,
                    source_root=out_dir,
                    evidence_tier=EvidenceTier.DERIVED,
                    parent_id=artifact.artifact_id,
                    derivation_step="media_extract_audio",
                    tool="ffmpeg",
                    reproducibility={"replayable": True},
                )
            )
        summary["processed"].append(
            {
                "artifact_id": artifact.artifact_id,
                "probe": json.loads(probe_result.stdout) if probe_result.stdout else {},
                "frame_probe": json.loads(frame_probe.stdout) if frame_probe.stdout else {},
                "frames": frame_records,
                "audio_path": str(audio_path) if audio_path.exists() else None,
            }
        )
    if not dry_run:
        append_artifact_store(settings.workspace, derived)
        (paths["analysis"] / "media_extract.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
