from pathlib import Path

from x1371.manifest import (
    append_artifact_store,
    build_artifact_record,
    compute_hashes,
    load_artifact_store,
    save_artifact_store,
)
from x1371.models import EvidenceTier
from x1371.provenance import build_lineage


def test_hashing_and_manifest_round_trip(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("11B-X-1371")
    hashes = compute_hashes(sample)
    assert hashes["sha256"]
    record = build_artifact_record(sample, source_root=tmp_path)
    save_artifact_store(tmp_path, [record])
    loaded = load_artifact_store(tmp_path)
    assert loaded[0].hashes == hashes
    assert loaded[0].logical_path == "sample.txt"


def test_lineage_and_evidence_tiers_are_tracked(tmp_path: Path) -> None:
    primary = tmp_path / "primary.txt"
    derived = tmp_path / "derived.txt"
    primary.write_text("abc")
    derived.write_text("cba")
    parent = build_artifact_record(primary, source_root=tmp_path, evidence_tier=EvidenceTier.PRIMARY)
    child = build_artifact_record(
        derived,
        source_root=tmp_path,
        evidence_tier=EvidenceTier.DERIVED,
        parent_id=parent.artifact_id,
        derivation_step="reverse",
        tool="unit-test",
    )
    append_artifact_store(tmp_path, [parent, child])
    lineage = build_lineage([parent, child])
    assert lineage[parent.artifact_id] == [child.artifact_id]
    assert parent.evidence_tier is EvidenceTier.PRIMARY
    assert child.evidence_tier is EvidenceTier.DERIVED
