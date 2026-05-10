from __future__ import annotations

import argparse
import json
from typing import Any

from .analysis.extraction import expand_archives
from .analysis.metadata import extract_metadata
from .analysis.ocr import run_ocr
from .analysis.text_analysis import analyze_texts, collect_text_artifacts
from .claims import ingest_claim_paths
from .config import Settings, load_settings
from .ingest import ingest_paths
from .logging_utils import configure_logging
from .manifest import load_artifact_store
from .media.enhance import enhance_artifacts
from .media.extract import extract_media
from .models import DecodeNode
from .pipeline import (
    run_all,
    run_claim_comparison,
    run_correlation_stage,
    run_decode_stage,
    run_determinism_stage,
)
from .reporting import generate_reports, load_workspace_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="x1371", description="11B-X-1371 forensic analysis toolkit")
    parser.add_argument("--config", help="Path to TOML configuration file")
    parser.add_argument("--workspace", help="Override workspace directory")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose structured logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest source evidence")
    ingest_parser.add_argument("inputs", nargs="+", help="Input files or directories")
    ingest_parser.add_argument("--dry-run", action="store_true")

    inventory_parser = subparsers.add_parser("inventory", help="Show current inventory")
    inventory_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    for name, help_text in [
        ("metadata", "Extract metadata"),
        ("expand", "Expand archives"),
        ("media-extract", "Extract media components"),
        ("enhance", "Generate reversible enhancement variants"),
        ("ocr", "Run OCR on image artifacts"),
        ("text-scan", "Analyze Unicode and heuristic text signals"),
        ("decode", "Run layered decode exploration"),
        ("correlate", "Correlate artifact text and lineage"),
        ("determinism", "Re-run deterministic stages"),
        ("report", "Generate JSON and Markdown reports"),
    ]:
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--dry-run", action="store_true")

    run_all_parser = subparsers.add_parser("run-all", help="Execute the full offline pipeline")
    run_all_parser.add_argument("inputs", nargs="+", help="Input files or directories")
    run_all_parser.add_argument("--claims", nargs="*", default=[], help="Optional external claims to quarantine")
    run_all_parser.add_argument("--dry-run", action="store_true")

    claims_parser = subparsers.add_parser("ingest-claims", help="Ingest external claims into quarantine")
    claims_parser.add_argument("inputs", nargs="+", help="Claim files or directories")
    claims_parser.add_argument("--dry-run", action="store_true")

    compare_claims_parser = subparsers.add_parser("compare-claims", help="Compare claims against decode branches")
    compare_claims_parser.add_argument("--dry-run", action="store_true")
    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    overrides: dict[str, Any] = {}
    if args.workspace:
        overrides["workspace"] = args.workspace
    return load_settings(args.config, overrides=overrides)


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    settings = _settings_from_args(args)

    if args.command == "ingest":
        _print(ingest_paths(args.inputs, settings, dry_run=args.dry_run))
        return 0

    artifacts = load_artifact_store(settings.workspace)

    if args.command == "inventory":
        _print({"artifacts": [artifact.to_dict() for artifact in artifacts], "count": len(artifacts)})
        return 0
    if args.command == "metadata":
        _print(extract_metadata(artifacts, settings, dry_run=args.dry_run))
        return 0
    if args.command == "expand":
        _print(expand_archives(artifacts, settings, dry_run=args.dry_run))
        return 0
    if args.command == "media-extract":
        _print(extract_media(artifacts, settings, dry_run=args.dry_run))
        return 0
    if args.command == "enhance":
        _print(enhance_artifacts(artifacts, settings, dry_run=args.dry_run))
        return 0
    if args.command == "ocr":
        _print(run_ocr(artifacts, settings, dry_run=args.dry_run))
        return 0
    if args.command == "text-scan":
        _print(analyze_texts(collect_text_artifacts(artifacts), settings, dry_run=args.dry_run))
        return 0
    if args.command == "decode":
        _print(run_decode_stage(collect_text_artifacts(artifacts), settings, dry_run=args.dry_run))
        return 0
    if args.command == "correlate":
        _print(run_correlation_stage(artifacts, collect_text_artifacts(artifacts), settings, dry_run=args.dry_run))
        return 0
    if args.command == "determinism":
        _print(run_determinism_stage(collect_text_artifacts(artifacts), settings, dry_run=args.dry_run))
        return 0
    if args.command == "report":
        payload = {"paths": generate_reports(load_workspace_context(settings), settings)} if not args.dry_run else {"dry_run": True}
        _print(payload)
        return 0
    if args.command == "run-all":
        _print(run_all(args.inputs, settings, claim_inputs=args.claims, dry_run=args.dry_run))
        return 0
    if args.command == "ingest-claims":
        _print(ingest_claim_paths(args.inputs, settings, dry_run=args.dry_run))
        return 0
    if args.command == "compare-claims":
        decode_path = settings.paths()["analysis"] / "decode.json"
        if not decode_path.exists():
            _print({"comparisons": [], "warning": "decode stage has not been run yet"})
            return 0
        nodes = [DecodeNode(**item) for item in json.loads(decode_path.read_text()).get("nodes", [])]
        _print(run_claim_comparison(settings, nodes, dry_run=args.dry_run))
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
