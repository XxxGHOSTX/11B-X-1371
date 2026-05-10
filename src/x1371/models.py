from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EvidenceTier(StrEnum):
    PRIMARY = "primary"
    DERIVED = "derived"
    HEURISTIC = "heuristic"
    EXTERNAL_CLAIM = "external_claim"


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    source_path: str
    logical_path: str
    artifact_class: str
    artifact_type: str
    detected_type: str | None
    size: int
    hashes: dict[str, str]
    created_at: str | None = None
    modified_at: str | None = None
    parent_id: str | None = None
    derivation_step: str | None = None
    tool: str | None = None
    transform_parameters: dict[str, Any] = field(default_factory=dict)
    reproducibility: dict[str, Any] = field(default_factory=dict)
    determinism: dict[str, Any] = field(default_factory=dict)
    suspicion_tags: list[str] = field(default_factory=list)
    evidence_tier: EvidenceTier = EvidenceTier.PRIMARY

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_tier"] = self.evidence_tier.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactRecord:
        payload = dict(data)
        payload["evidence_tier"] = EvidenceTier(payload["evidence_tier"])
        return cls(**payload)


@dataclass(slots=True)
class DecodeNode:
    node_id: str
    artifact_id: str
    parent_id: str | None
    depth: int
    transform_name: str
    parameters: dict[str, Any]
    output: str
    structuredness: dict[str, Any]
    validation_notes: list[str]
    residue: str
    score: float
    deterministic: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HeuristicLead:
    artifact_id: str
    analyzer: str
    summary: str
    details: dict[str, Any]
    evidence_tier: EvidenceTier = EvidenceTier.HEURISTIC

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_tier"] = self.evidence_tier.value
        return data


@dataclass(slots=True)
class CorrelationRecord:
    left_id: str
    right_id: str
    correlation_type: str
    score: float
    details: dict[str, Any]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeterminismRecord:
    step_name: str
    stable: bool
    digest: str
    iterations: int
    mismatches: list[dict[str, Any]]
    likely_causes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClaimComparison:
    claim_artifact_id: str
    branch_node_id: str | None
    overlap_score: float
    disposition: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProofCandidate:
    node_id: str
    artifact_id: str
    score: float
    proof_status: str
    rationale: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def now_utc() -> str:
    return datetime.now(tz=UTC).isoformat()
