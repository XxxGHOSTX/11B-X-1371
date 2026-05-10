from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class ExifToolAdapter(ExternalToolAdapter):
    def metadata(self, path: Path) -> ToolResult:
        return self.run("-json", str(path))
