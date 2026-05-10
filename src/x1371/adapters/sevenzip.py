from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class SevenZipAdapter(ExternalToolAdapter):
    def list(self, path: Path) -> ToolResult:
        return self.run("l", "-slt", str(path), timeout=600)

    def extract(self, path: Path, output_dir: Path) -> ToolResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        return self.run("x", "-y", f"-o{output_dir}", str(path), timeout=600)
