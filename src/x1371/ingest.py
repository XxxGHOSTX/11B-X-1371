from __future__ import annotations

import json
from pathlib import Path

from .config import Settings, ensure_workspace
from .manifest import (
    append_artifact_store,
    build_artifact_record,
    inventory_inputs,
    safe_link_or_copy,
    write_manifest,
)
from .models import ArtifactRecord, EvidenceTier, now_utc


def ingest_paths(
    inputs: list[str | Path],
    settings: Settings,
    *,
    claims: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    paths = ensure_workspace(settings)
    discovered = inventory_inputs([Path(item).resolve() for item in inputs])
    tier = EvidenceTier.EXTERNAL_CLAIM if claims else EvidenceTier.PRIMARY
    destination_root = paths["evidence_claims"] if claims else paths["evidence_primary"]
    records: list[ArtifactRecord] = []
    failures: list[dict[str, str]] = []
    for source in discovered:
        try:
            record = build_artifact_record(
                source,
                source_root=source.parent,
                evidence_tier=tier,
                suspicion_tags=["unverified_external_claim"] if claims else [],
                reproducibility={"preserved_original": True},
            )
            destination = destination_root / record.artifact_id / source.name
            if not dry_run:
                safe_link_or_copy(source, destination, hardlink=settings.hardlink_ingest and not claims)
            stored = build_artifact_record(
                destination if destination.exists() else source,
                source_root=destination.parent if destination.exists() else source.parent,
                evidence_tier=tier,
                suspicion_tags=record.suspicion_tags,
                reproducibility={"preserved_original": True, "storage_mode": "hardlink_or_copy"},
            )
            stored.source_path = str(source)
            stored.logical_path = record.logical_path
            records.append(stored)
        except Exception as exc:  # noqa: BLE001
            failures.append({"path": str(source), "error": str(exc)})
    if not dry_run:
        append_artifact_store(settings.workspace, records)
        timestamp = now_utc().replace(":", "-")
        manifest_path = paths["manifests"] / f"ingest-{timestamp}.json"
        write_manifest(records, manifest_path)
        (paths["manifests"] / "ingest-summary.json").write_text(
            json.dumps(
                {
                    "created_at": now_utc(),
                    "claims_mode": claims,
                    "artifacts": [record.to_dict() for record in records],
                    "failures": failures,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return {
        "artifact_count": len(records),
        "failures": failures,
        "artifacts": [record.to_dict() for record in records],
    }
