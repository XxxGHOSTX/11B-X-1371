from __future__ import annotations

from .models import ClaimComparison, DecodeNode, ProofCandidate


def proof_status(score: float) -> str:
    if score >= 80:
        return "proven"
    if score >= 60:
        return "strongly_supported"
    if score >= 35:
        return "tentative"
    if score >= 15:
        return "unsupported"
    return "rejected"


def rank_candidates(
    nodes: list[DecodeNode],
    *,
    cross_source_support: dict[str, int] | None = None,
    stable_nodes: set[str] | None = None,
    claim_comparisons: list[ClaimComparison] | None = None,
) -> list[ProofCandidate]:
    support = cross_source_support or {}
    stable = stable_nodes or set()
    claim_penalties = {comparison.branch_node_id: comparison.overlap_score for comparison in claim_comparisons or []}
    ranked: list[ProofCandidate] = []
    for node in nodes:
        if node.depth == 0:
            continue
        score = node.score
        score += support.get(node.node_id, 0) * 8
        score += 5 if node.node_id in stable else 0
        score -= claim_penalties.get(node.node_id, 0.0) * 20
        score -= len(node.residue) * 2
        rationale = [
            f"base score {node.score:.2f}",
            f"cross-source support {support.get(node.node_id, 0)}",
            "stable across reruns" if node.node_id in stable else "not determinism-validated",
        ]
        if node.node_id in claim_penalties:
            rationale.append("penalized for alignment with external claims without independent proof")
        ranked.append(
            ProofCandidate(
                node_id=node.node_id,
                artifact_id=node.artifact_id,
                score=round(score, 3),
                proof_status=proof_status(score),
                rationale=rationale,
            )
        )
    return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)
