from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TOOL_PATHS = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "exiftool": "exiftool",
    "sevenzip": "7z",
    "binwalk": "binwalk",
    "tesseract": "tesseract",
    "file": "file",
    "strings": "strings",
    "imagemagick": "magick",
}

DEFAULT_ENHANCEMENTS = [
    "grayscale",
    "autocontrast",
    "equalize",
    "threshold",
    "invert",
    "sharpen",
    "denoise",
    "edge_enhance",
    "upscale2x",
    "rotate90",
    "rotate180",
    "flip_horizontal",
    "flip_vertical",
    "channel_red",
    "channel_green",
    "channel_blue",
]

DEFAULT_OCR_PASSES = [
    {"name": "default", "lang": "eng", "psm": 6, "oem": 1},
    {"name": "sparse", "lang": "eng", "psm": 11, "oem": 1},
]


@dataclass(slots=True)
class Settings:
    workspace: Path = Path(".x1371")
    decode_depth: int = 2
    decode_max_nodes: int = 250
    archive_recursion_limit: int = 3
    hardlink_ingest: bool = True
    compute_frame_hashes: bool = True
    enhancement_variants: list[str] = field(default_factory=lambda: list(DEFAULT_ENHANCEMENTS))
    ocr_passes: list[dict[str, Any]] = field(default_factory=lambda: copy.deepcopy(DEFAULT_OCR_PASSES))
    tool_paths: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TOOL_PATHS))

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Settings:
        return cls(
            workspace=Path(data.get("workspace", ".x1371")),
            decode_depth=int(data.get("decode_depth", 2)),
            decode_max_nodes=int(data.get("decode_max_nodes", 250)),
            archive_recursion_limit=int(data.get("archive_recursion_limit", 3)),
            hardlink_ingest=bool(data.get("hardlink_ingest", True)),
            compute_frame_hashes=bool(data.get("compute_frame_hashes", True)),
            enhancement_variants=list(data.get("enhancement_variants", DEFAULT_ENHANCEMENTS)),
            ocr_passes=list(data.get("ocr_passes", copy.deepcopy(DEFAULT_OCR_PASSES))),
            tool_paths={**DEFAULT_TOOL_PATHS, **dict(data.get("tool_paths", {}))},
        )

    def paths(self) -> dict[str, Path]:
        workspace = self.workspace
        return {
            "workspace": workspace,
            "evidence_primary": workspace / "evidence" / "primary",
            "evidence_derived": workspace / "evidence" / "derived",
            "evidence_heuristic": workspace / "evidence" / "heuristic",
            "evidence_claims": workspace / "evidence" / "external_claims",
            "manifests": workspace / "manifests",
            "metadata": workspace / "metadata",
            "analysis": workspace / "analysis",
            "reports": workspace / "reports",
            "logs": workspace / "logs",
            "tmp": workspace / "tmp",
        }


def default_settings_payload() -> dict[str, Any]:
    return {
        "workspace": ".x1371",
        "decode_depth": 2,
        "decode_max_nodes": 250,
        "archive_recursion_limit": 3,
        "hardlink_ingest": True,
        "compute_frame_hashes": True,
        "enhancement_variants": list(DEFAULT_ENHANCEMENTS),
        "ocr_passes": copy.deepcopy(DEFAULT_OCR_PASSES),
        "tool_paths": dict(DEFAULT_TOOL_PATHS),
    }


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(config_path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> Settings:
    config_data: dict[str, Any] = {}
    if config_path:
        with Path(config_path).open("rb") as handle:
            config_data = tomllib.load(handle)
    merged = deep_merge(default_settings_payload(), config_data)
    if overrides:
        merged = deep_merge(merged, overrides)
    return Settings.from_mapping(merged)


def ensure_workspace(settings: Settings) -> dict[str, Path]:
    paths = settings.paths()
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
