from __future__ import annotations

from itertools import combinations

from .models import ArtifactRecord, CorrelationRecord
from .text_utils import tokenize


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def correlate_artifacts(
    artifacts: list[ArtifactRecord],
    text_map: dict[str, str],
) -> list[CorrelationRecord]:
    record_map = {artifact.artifact_id: artifact for artifact in artifacts}
    correlations: list[CorrelationRecord] = []
    for left_id, right_id in combinations(sorted(text_map), 2):
        left_tokens = set(tokenize(text_map[left_id]))
        right_tokens = set(tokenize(text_map[right_id]))
        token_overlap = _jaccard(left_tokens, right_tokens)
        if token_overlap > 0:
            correlations.append(
                CorrelationRecord(
                    left_id=left_id,
                    right_id=right_id,
                    correlation_type="token_overlap",
                    score=round(token_overlap, 3),
                    details={"shared_tokens": sorted(left_tokens & right_tokens)[:25]},
                    summary="Normalized token overlap detected",
                )
            )
        if record_map[left_id].hashes.get("sha256") and record_map[left_id].hashes == record_map[right_id].hashes:
            correlations.append(
                CorrelationRecord(
                    left_id=left_id,
                    right_id=right_id,
                    correlation_type="hash_equality",
                    score=1.0,
                    details={"sha256": record_map[left_id].hashes.get("sha256")},
                    summary="Artifacts share identical hashes",
                )
            )
        filename_overlap = _jaccard(
            set(tokenize(record_map[left_id].logical_path)),
            set(tokenize(record_map[right_id].logical_path)),
        )
        if filename_overlap > 0:
            correlations.append(
                CorrelationRecord(
                    left_id=left_id,
                    right_id=right_id,
                    correlation_type="path_clue_overlap",
                    score=round(filename_overlap, 3),
                    details={"left": record_map[left_id].logical_path, "right": record_map[right_id].logical_path},
                    summary="Logical path clue overlap detected",
                )
            )
        if record_map[left_id].parent_id == right_id or record_map[right_id].parent_id == left_id:
            correlations.append(
                CorrelationRecord(
                    left_id=left_id,
                    right_id=right_id,
                    correlation_type="derivation_link",
                    score=1.0,
                    details={"parent_child": True},
                    summary="Direct derivation relationship recorded",
                )
            )
    return correlations
