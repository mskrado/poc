"""Offline demo. No Ollama."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_demo_all_replays_shipped_run():
    result = subprocess.run(
        [sys.executable, str(ROOT / "demo.py"), "--scenario", "all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "in_tok= 21125" in out
    assert "route_human=36" in out
    assert "seed-orion-tool-output" in out
    assert "seed-orion-memory" in out
    assert "| 0.8 | 36 | 7 | 29 | 14 | 0 |" in out
    assert "$" not in out
