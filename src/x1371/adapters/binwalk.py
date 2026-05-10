from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class BinwalkAdapter(ExternalToolAdapter):
    def scan(self, path: Path) -> ToolResult:
        return self.run("--json", str(path), timeout=600)
