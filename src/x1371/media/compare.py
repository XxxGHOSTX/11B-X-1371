from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:  # pragma: no cover - optional dependency
    Image = None
    ImageChops = None


def frame_difference(left: Path, right: Path, output: Path) -> bool:
    if Image is None or ImageChops is None:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(left) as left_image, Image.open(right) as right_image:
        diff = ImageChops.difference(left_image.convert("RGB"), right_image.convert("RGB"))
        diff.save(output)
    return True
