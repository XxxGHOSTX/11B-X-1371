from x1371.decode.engine import run_layered_decode
from x1371.models import ClaimComparison
from x1371.ranking import rank_candidates


def test_ranking_penalizes_external_claim_alignment() -> None:
    nodes = [node for node in run_layered_decode("artifact", "cba", max_depth=1, max_nodes=20) if node.depth > 0]
    baseline = rank_candidates(nodes)
    penalized = rank_candidates(
        nodes,
        claim_comparisons=[
            ClaimComparison(
                claim_artifact_id="claim",
                branch_node_id=baseline[0].node_id,
                overlap_score=1.0,
                disposition="correlation",
                summary="alignment",
            )
        ],
    )
    assert penalized[0].score <= baseline[0].score
