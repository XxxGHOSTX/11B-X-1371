from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .manifest import build_artifact_record
from .models import ArtifactRecord, EvidenceTier


def derive_artifact(
    parent: ArtifactRecord,
    output_path: Path,
    *,
    artifact_tier: EvidenceTier = EvidenceTier.DERIVED,
    derivation_step: str,
    tool: str,
    transform_parameters: dict[str, object] | None = None,
    suspicion_tags: list[str] | None = None,
) -> ArtifactRecord:
    record = build_artifact_record(
        output_path,
        source_root=output_path.parent,
        evidence_tier=artifact_tier,
        parent_id=parent.artifact_id,
        derivation_step=derivation_step,
        tool=tool,
        transform_parameters=transform_parameters,
        suspicion_tags=suspicion_tags,
        reproducibility={"replayable": True},
    )
    return record


def build_lineage(records: list[ArtifactRecord]) -> dict[str, list[str]]:
    lineage: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.parent_id:
            lineage[record.parent_id].append(record.artifact_id)
    return dict(lineage)


def walk_lineage(start_id: str, records: list[ArtifactRecord]) -> list[ArtifactRecord]:
    record_map = {record.artifact_id: record for record in records}
    lineage = build_lineage(records)
    ordered: list[ArtifactRecord] = []
    queue = [start_id]
    while queue:
        current = queue.pop(0)
        if current in record_map:
            ordered.append(record_map[current])
        queue.extend(lineage.get(current, []))
    return ordered
