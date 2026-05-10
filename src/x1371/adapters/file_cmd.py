from __future__ import annotations

import mimetypes
from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class FileCommandAdapter(ExternalToolAdapter):
    def identify(self, path: Path) -> ToolResult:
        result = self.run("--brief", "--mime-type", str(path))
        if result.available and result.returncode == 0:
            return result
        guessed, _ = mimetypes.guess_type(path.name)
        return ToolResult(self.name, [self.executable, str(path)], False, 0, guessed or "application/octet-stream", "")
