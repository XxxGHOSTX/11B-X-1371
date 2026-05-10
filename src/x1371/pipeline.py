from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .analysis.extraction import expand_archives
from .analysis.metadata import extract_metadata
from .analysis.ocr import run_ocr
from .analysis.text_analysis import analyze_texts, collect_text_artifacts
from .claims import compare_claims_to_branches, ingest_claim_paths
from .config import Settings, ensure_workspace
from .decode.engine import run_layered_decode
from .determinism import validate_determinism
from .ingest import ingest_paths
from .manifest import load_artifact_store
from .media.enhance import enhance_artifacts
from .media.extract import extract_media
from .models import ClaimComparison, DecodeNode
from .ranking import rank_candidates
from .reporting import generate_reports, load_workspace_context
from .text_utils import read_text_file


def run_decode_stage(text_map: dict[str, str], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    nodes: list[DecodeNode] = []
    for artifact_id, text in text_map.items():
        nodes.extend(
            run_layered_decode(
                artifact_id,
                text,
                max_depth=settings.decode_depth,
                max_nodes=settings.decode_max_nodes,
            )
        )
    payload = {"nodes": [node.to_dict() for node in nodes]}
    if not dry_run:
        paths = ensure_workspace(settings)
        (paths["analysis"] / "decode.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def run_correlation_stage(artifacts: list[object], text_map: dict[str, str], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    from .correlation import correlate_artifacts

    correlations = correlate_artifacts(artifacts, text_map)
    payload = {"correlations": [correlation.to_dict() for correlation in correlations]}
    if not dry_run:
        paths = ensure_workspace(settings)
        (paths["analysis"] / "correlations.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def run_determinism_stage(text_map: dict[str, str], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for artifact_id, text in list(text_map.items())[:5]:
        record = validate_determinism(
            f"unicode_analysis:{artifact_id}",
            runner=lambda current_text=text, current_id=artifact_id: analyze_texts(
                {current_id: current_text}, settings, dry_run=True
            ),
        )
        checks[artifact_id] = record.to_dict()
    if not dry_run:
        paths = ensure_workspace(settings)
        (paths["analysis"] / "determinism.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False))
    return checks


def run_claim_comparison(settings: Settings, branches: list[DecodeNode], *, dry_run: bool = False) -> dict[str, Any]:
    artifacts = load_artifact_store(settings.workspace)
    claim_texts = {
        artifact.artifact_id: read_text_file(Path(artifact.source_path))
        for artifact in artifacts
        if artifact.evidence_tier.value == "external_claim" and Path(artifact.source_path).exists()
    }
    comparisons = compare_claims_to_branches(claim_texts, branches)
    payload = {"comparisons": [comparison.to_dict() for comparison in comparisons]}
    if not dry_run:
        paths = ensure_workspace(settings)
        (paths["analysis"] / "claims_comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def run_ranking_stage(
    decode_payload: dict[str, Any],
    correlation_payload: dict[str, Any],
    determinism_payload: dict[str, Any],
    claim_payload: dict[str, Any],
    settings: Settings,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    nodes = [DecodeNode(**item) for item in decode_payload.get("nodes", []) if item["depth"] > 0]
    support: dict[str, int] = {}
    for correlation in correlation_payload.get("correlations", []):
        support[correlation["left_id"]] = support.get(correlation["left_id"], 0) + 1
        support[correlation["right_id"]] = support.get(correlation["right_id"], 0) + 1
    stable_artifacts = {artifact_id for artifact_id, record in determinism_payload.items() if record.get("stable")}
    stable_nodes = {node.node_id for node in nodes if node.artifact_id in stable_artifacts}
    claim_comparisons = [ClaimComparison(**item) for item in claim_payload.get("comparisons", [])]
    ranked = rank_candidates(
        nodes,
        cross_source_support=support,
        stable_nodes=stable_nodes,
        claim_comparisons=claim_comparisons,
    )
    payload = {"candidates": [candidate.to_dict() for candidate in ranked]}
    if not dry_run:
        paths = ensure_workspace(settings)
        (paths["analysis"] / "ranking.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def run_all(inputs: list[str], settings: Settings, *, claim_inputs: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    ensure_workspace(settings)
    summary: dict[str, Any] = {}
    summary["ingest"] = ingest_paths(inputs, settings, dry_run=dry_run)
    if claim_inputs:
        summary["claims_ingest"] = ingest_claim_paths(claim_inputs, settings, dry_run=dry_run)
    artifacts = load_artifact_store(settings.workspace)
    summary["metadata"] = extract_metadata(artifacts, settings, dry_run=dry_run)
    summary["expand"] = expand_archives(artifacts, settings, dry_run=dry_run)
    artifacts = load_artifact_store(settings.workspace)
    summary["media"] = extract_media(artifacts, settings, dry_run=dry_run)
    artifacts = load_artifact_store(settings.workspace)
    summary["enhance"] = enhance_artifacts(artifacts, settings, dry_run=dry_run)
    artifacts = load_artifact_store(settings.workspace)
    summary["ocr"] = run_ocr(artifacts, settings, dry_run=dry_run)
    artifacts = load_artifact_store(settings.workspace)
    text_map = collect_text_artifacts(artifacts)
    summary["text_analysis"] = analyze_texts(text_map, settings, dry_run=dry_run)
    summary["decode"] = run_decode_stage(text_map, settings, dry_run=dry_run)
    summary["correlate"] = run_correlation_stage(artifacts, text_map, settings, dry_run=dry_run)
    summary["determinism"] = run_determinism_stage(text_map, settings, dry_run=dry_run)
    nodes = [DecodeNode(**item) for item in summary["decode"].get("nodes", [])]
    summary["claims_compare"] = run_claim_comparison(settings, nodes, dry_run=dry_run)
    summary["ranking"] = run_ranking_stage(
        summary["decode"],
        summary["correlate"],
        summary["determinism"],
        summary["claims_compare"],
        settings,
        dry_run=dry_run,
    )
    if not dry_run:
        context = load_workspace_context(settings)
        summary["report"] = generate_reports(context, settings)
    return summary
