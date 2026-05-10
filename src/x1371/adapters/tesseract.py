from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class TesseractAdapter(ExternalToolAdapter):
    def ocr(self, path: Path, output_base: Path, *, lang: str = "eng", psm: int = 6, oem: int = 1) -> ToolResult:
        output_base.parent.mkdir(parents=True, exist_ok=True)
        return self.run(str(path), str(output_base), "-l", lang, "--psm", str(psm), "--oem", str(oem), timeout=600)
