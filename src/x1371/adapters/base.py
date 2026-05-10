from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ToolResult:
    tool: str
    command: list[str]
    available: bool
    returncode: int | None
    stdout: str
    stderr: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ExternalToolAdapter:
    def __init__(self, name: str, executable: str) -> None:
        self.name = name
        self.executable = executable

    def available(self) -> bool:
        return shutil.which(self.executable) is not None

    def run(self, *args: str, cwd: Path | None = None, timeout: int = 300) -> ToolResult:
        command = [self.executable, *args]
        if not self.available():
            return ToolResult(self.name, command, False, None, "", "", "tool not installed")
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return ToolResult(
            tool=self.name,
            command=command,
            available=True,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            error=None if completed.returncode == 0 else f"command exited with {completed.returncode}",
        )
