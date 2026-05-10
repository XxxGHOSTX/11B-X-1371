from __future__ import annotations

from .ingest import ingest_paths
from .models import ClaimComparison, DecodeNode
from .text_utils import tokenize


def ingest_claim_paths(inputs: list[str], settings: object, *, dry_run: bool = False) -> dict[str, object]:
    return ingest_paths(inputs, settings, claims=True, dry_run=dry_run)


def compare_claims_to_branches(claim_texts: dict[str, str], branches: list[DecodeNode]) -> list[ClaimComparison]:
    comparisons: list[ClaimComparison] = []
    branch_tokens = {branch.node_id: set(tokenize(branch.output)) for branch in branches}
    for claim_id, text in claim_texts.items():
        claim_tokens = set(tokenize(text))
        best_node = None
        best_score = 0.0
        for node_id, tokens in branch_tokens.items():
            if not tokens or not claim_tokens:
                overlap = 0.0
            else:
                overlap = len(tokens & claim_tokens) / len(tokens | claim_tokens)
            if overlap > best_score:
                best_score = overlap
                best_node = node_id
        disposition = "correlation" if best_score > 0 else "unsupported"
        comparisons.append(
            ClaimComparison(
                claim_artifact_id=claim_id,
                branch_node_id=best_node,
                overlap_score=round(best_score, 3),
                disposition=disposition,
                summary="External claim compared against independently derived branch output",
            )
        )
    return comparisons
