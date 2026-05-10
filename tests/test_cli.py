from pathlib import Path

from x1371.cli import main


def test_cli_smoke_ingest_and_inventory(tmp_path: Path, capsys: object) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("11B-X-1371")
    workspace = tmp_path / ".x1371"
    assert main(["--workspace", str(workspace), "ingest", str(sample)]) == 0
    captured = capsys.readouterr()
    assert "artifact_count" in captured.out
    assert main(["--workspace", str(workspace), "inventory"]) == 0
