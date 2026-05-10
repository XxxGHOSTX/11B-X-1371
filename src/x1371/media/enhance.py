from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..config import Settings, ensure_workspace
from ..manifest import append_artifact_store, build_artifact_record
from ..models import ArtifactRecord, EvidenceTier

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:  # pragma: no cover - optional dependency
    Image = None
    ImageFilter = None
    ImageOps = None


Enhancement = Callable[[Any], list[tuple[str, Any]]]


class EnhancementRegistry:
    def __init__(self) -> None:
        self._enhancements: dict[str, Enhancement] = {}

    def register(self, name: str) -> Callable[[Enhancement], Enhancement]:
        def decorator(func: Enhancement) -> Enhancement:
            self._enhancements[name] = func
            return func

        return decorator

    def get(self, name: str) -> Enhancement | None:
        return self._enhancements.get(name)


registry = EnhancementRegistry()


@registry.register("grayscale")
def grayscale(image: Any) -> list[tuple[str, Any]]:
    return [("grayscale", ImageOps.grayscale(image))]


@registry.register("autocontrast")
def autocontrast(image: Any) -> list[tuple[str, Any]]:
    return [("autocontrast", ImageOps.autocontrast(image))]


@registry.register("equalize")
def equalize(image: Any) -> list[tuple[str, Any]]:
    return [("equalize", ImageOps.equalize(image.convert("L")))]


@registry.register("threshold")
def threshold(image: Any) -> list[tuple[str, Any]]:
    grey = image.convert("L")
    return [("threshold", grey.point(lambda pixel: 255 if pixel > 128 else 0))]


@registry.register("invert")
def invert(image: Any) -> list[tuple[str, Any]]:
    return [("invert", ImageOps.invert(image.convert("RGB")))]


@registry.register("sharpen")
def sharpen(image: Any) -> list[tuple[str, Any]]:
    return [("sharpen", image.filter(ImageFilter.SHARPEN))]


@registry.register("denoise")
def denoise(image: Any) -> list[tuple[str, Any]]:
    return [("denoise", image.filter(ImageFilter.SMOOTH_MORE))]


@registry.register("edge_enhance")
def edge_enhance(image: Any) -> list[tuple[str, Any]]:
    return [("edge_enhance", image.filter(ImageFilter.EDGE_ENHANCE_MORE))]


@registry.register("upscale2x")
def upscale(image: Any) -> list[tuple[str, Any]]:
    return [("upscale2x", image.resize((image.width * 2, image.height * 2)))]


@registry.register("rotate90")
def rotate90(image: Any) -> list[tuple[str, Any]]:
    return [("rotate90", image.rotate(90, expand=True))]


@registry.register("rotate180")
def rotate180(image: Any) -> list[tuple[str, Any]]:
    return [("rotate180", image.rotate(180, expand=True))]


@registry.register("flip_horizontal")
def flip_horizontal(image: Any) -> list[tuple[str, Any]]:
    return [("flip_horizontal", ImageOps.mirror(image))]


@registry.register("flip_vertical")
def flip_vertical(image: Any) -> list[tuple[str, Any]]:
    return [("flip_vertical", ImageOps.flip(image))]


@registry.register("channel_red")
def channel_red(image: Any) -> list[tuple[str, Any]]:
    red, _, _ = image.convert("RGB").split()
    return [("channel_red", red)]


@registry.register("channel_green")
def channel_green(image: Any) -> list[tuple[str, Any]]:
    _, green, _ = image.convert("RGB").split()
    return [("channel_green", green)]


@registry.register("channel_blue")
def channel_blue(image: Any) -> list[tuple[str, Any]]:
    _, _, blue = image.convert("RGB").split()
    return [("channel_blue", blue)]


def enhance_artifacts(artifacts: list[ArtifactRecord], settings: Settings, *, dry_run: bool = False) -> dict[str, Any]:
    paths = ensure_workspace(settings)
    derived: list[ArtifactRecord] = []
    summary: dict[str, Any] = {"generated": [], "skipped": []}
    if Image is None or ImageOps is None or ImageFilter is None:
        summary["skipped"].append({"reason": "Pillow not installed"})
        return summary
    for artifact in artifacts:
        source = Path(artifact.source_path)
        if artifact.artifact_class != "image":
            continue
        output_dir = paths["evidence_derived"] / "enhancements" / artifact.artifact_id
        if dry_run:
            continue
        with Image.open(source) as image:
            for variant_name in settings.enhancement_variants:
                enhancement = registry.get(variant_name)
                if enhancement is None:
                    continue
                for label, enhanced_image in enhancement(image):
                    target = output_dir / f"{label}{source.suffix or '.png'}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    enhanced_image.save(target)
                    record = build_artifact_record(
                        target,
                        source_root=output_dir,
                        evidence_tier=EvidenceTier.DERIVED,
                        parent_id=artifact.artifact_id,
                        derivation_step="enhance_image",
                        tool="pillow",
                        transform_parameters={"variant": label},
                        reproducibility={"replayable": True},
                        determinism={"expected_stable": True},
                        suspicion_tags=["analysis_derivative"],
                    )
                    derived.append(record)
                    summary["generated"].append(record.to_dict())
    if not dry_run:
        append_artifact_store(settings.workspace, derived)
        (paths["analysis"] / "enhancements.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary
