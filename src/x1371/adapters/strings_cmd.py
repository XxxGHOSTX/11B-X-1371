from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class StringsAdapter(ExternalToolAdapter):
    def extract(self, path: Path, minimum_length: int = 4) -> ToolResult:
        return self.run("-n", str(minimum_length), str(path))
