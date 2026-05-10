from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .config import Settings, ensure_workspace
from .manifest import load_artifact_store
from .models import ArtifactRecord, ProofCandidate, now_utc

SectionBuilder = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class ReportSection:
    name: str
    builder: SectionBuilder


class ReportRegistry:
    def __init__(self) -> None:
        self._sections: list[ReportSection] = []

    def register(self, name: str) -> Callable[[SectionBuilder], SectionBuilder]:
        def decorator(func: SectionBuilder) -> SectionBuilder:
            self._sections.append(ReportSection(name=name, builder=func))
            return func

        return decorator

    def build(self, context: dict[str, Any]) -> dict[str, Any]:
        return {section.name: section.builder(context) for section in self._sections}


registry = ReportRegistry()


@registry.register("inventory")
def inventory_section(context: dict[str, Any]) -> dict[str, Any]:
    artifacts: list[ArtifactRecord] = context["artifacts"]
    tiers = {artifact.evidence_tier.value for artifact in artifacts}
    return {
        "artifact_count": len(artifacts),
        "tiers": {tier: sum(1 for artifact in artifacts if artifact.evidence_tier.value == tier) for tier in tiers},
    }


@registry.register("metadata")
def metadata_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("metadata", {})


@registry.register("text_analysis")
def text_analysis_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("text_analysis", {})


@registry.register("decode_tree")
def decode_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("decode", {})


@registry.register("correlations")
def correlations_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("correlations", {})


@registry.register("determinism")
def determinism_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("determinism", {})


@registry.register("external_claims")
def claims_section(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("claims", {})


@registry.register("proof_ranking")
def ranking_section(context: dict[str, Any]) -> dict[str, Any]:
    candidates: list[ProofCandidate] = context.get("ranking", [])
    return {"candidates": [candidate.to_dict() for candidate in candidates]}


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# 11B-X-1371 Analysis Report", "", f"Generated: {now_utc()}", ""]
    for name, content in report.items():
        lines.append(f"## {name.replace('_', ' ').title()}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(content, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def generate_reports(context: dict[str, Any], settings: Settings) -> dict[str, str]:
    paths = ensure_workspace(settings)
    payload = registry.build(context)
    timestamp = now_utc().replace(":", "-")
    json_path = paths["reports"] / f"report-{timestamp}.json"
    md_path = paths["reports"] / f"report-{timestamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    md_path.write_text(render_markdown(payload))
    return {"json": str(json_path), "markdown": str(md_path)}


def load_workspace_context(settings: Settings) -> dict[str, Any]:
    paths = ensure_workspace(settings)
    artifacts = load_artifact_store(settings.workspace)
    context: dict[str, Any] = {"artifacts": artifacts}
    for name, filename in {
        "metadata": paths["metadata"] / "summary.json",
        "text_analysis": paths["analysis"] / "text_analysis.json",
        "decode": paths["analysis"] / "decode.json",
        "correlations": paths["analysis"] / "correlations.json",
        "determinism": paths["analysis"] / "determinism.json",
        "claims": paths["analysis"] / "claims_comparison.json",
        "ranking": paths["analysis"] / "ranking.json",
    }.items():
        if not filename.exists():
            continue
        payload = json.loads(filename.read_text())
        if name == "ranking":
            context[name] = [ProofCandidate(**item) for item in payload.get("candidates", [])]
        else:
            context[name] = payload
    return context
