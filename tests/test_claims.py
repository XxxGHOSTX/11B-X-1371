from pathlib import Path

from x1371.claims import compare_claims_to_branches, ingest_claim_paths
from x1371.config import Settings
from x1371.decode.engine import run_layered_decode
from x1371.manifest import load_artifact_store


def test_claims_are_quarantined_and_compared(tmp_path: Path) -> None:
    claim = tmp_path / "claim.txt"
    claim.write_text("abc")
    settings = Settings(workspace=tmp_path / ".x1371")
    ingest_claim_paths([str(claim)], settings)
    artifacts = load_artifact_store(settings.workspace)
    assert artifacts[0].evidence_tier.value == "external_claim"
    branches = run_layered_decode("artifact", "cba", max_depth=1, max_nodes=20)
    comparisons = compare_claims_to_branches({artifacts[0].artifact_id: "abc"}, branches)
    assert comparisons[0].disposition == "correlation"
