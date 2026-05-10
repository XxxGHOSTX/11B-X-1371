from __future__ import annotations

from pathlib import Path

from .base import ExternalToolAdapter, ToolResult


class FFmpegAdapter:
    def __init__(self, ffmpeg_path: str, ffprobe_path: str) -> None:
        self.ffmpeg = ExternalToolAdapter("ffmpeg", ffmpeg_path)
        self.ffprobe = ExternalToolAdapter("ffprobe", ffprobe_path)

    def available(self) -> bool:
        return self.ffmpeg.available() and self.ffprobe.available()

    def probe(self, path: Path) -> ToolResult:
        return self.ffprobe.run(
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        )

    def probe_frames(self, path: Path) -> ToolResult:
        return self.ffprobe.run(
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time,pict_type",
            str(path),
            timeout=600,
        )

    def extract_frames(self, source: Path, target_pattern: Path) -> ToolResult:
        target_pattern.parent.mkdir(parents=True, exist_ok=True)
        return self.ffmpeg.run("-y", "-i", str(source), "-vsync", "0", str(target_pattern), timeout=600)

    def extract_audio(self, source: Path, target_path: Path) -> ToolResult:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return self.ffmpeg.run("-y", "-i", str(source), "-vn", "-acodec", "copy", str(target_path), timeout=600)
