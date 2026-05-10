from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class ImageMagickAdapter(ExternalToolAdapter):
    def identify(self, path: Path) -> ToolResult:
        return self.run("identify", str(path))
