from pathlib import Path

from x1371.correlation import correlate_artifacts
from x1371.manifest import build_artifact_record


def test_correlation_detects_token_overlap(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("cipher moon signal")
    right.write_text("signal moon vector")
    left_record = build_artifact_record(left, source_root=tmp_path)
    right_record = build_artifact_record(right, source_root=tmp_path)
    correlations = correlate_artifacts(
        [left_record, right_record],
        {left_record.artifact_id: left.read_text(), right_record.artifact_id: right.read_text()},
    )
    assert any(item.correlation_type == "token_overlap" for item in correlations)
