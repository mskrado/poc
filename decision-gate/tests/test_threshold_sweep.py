"""Router threshold sweep from the shipped results. No model calls."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from gate.sweep import sweep_router

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not (ROOT / "results" / "results.csv").exists(), reason="shipped results missing")
def test_sweep_at_0_8_matches_summary():
    summary = json.loads((ROOT / "results" / "summary.json").read_text())
    with open(ROOT / "results" / "results.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    row = sweep_router(rows, [0.8])[0]
    reasons = summary["gate"]["route_reason_counts"]
    fallback = sum(v for k, v in reasons.items() if k.startswith("low_confidence_fallback"))
    assert row["tickets"] == summary["tickets"] == 50
    assert row["route_human"] == summary["gate"]["route_action_counts"]["route_human"]
    assert row["confident_human"] == reasons["model_choice:human"]
    assert row["low_confidence_fallback"] == fallback
    assert row["route_small"] == summary["gate"]["route_action_counts"]["route_small"]
    assert row["route_frontier"] == 0


def test_sweep_script_prints_table():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "threshold_sweep.py")],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr
    assert "| 0.8 | 36 | 7 | 29 | 14 | 0 |" in r.stdout


def test_cases_flag_is_in_help_and_conflicts_with_report_only():
    help_run = subprocess.run([sys.executable, str(ROOT / "run.py"), "--help"],
                              cwd=ROOT, capture_output=True, text=True, check=False)
    assert help_run.returncode == 0
    assert "--cases" in help_run.stdout
    conflict = subprocess.run([sys.executable, str(ROOT / "run.py"), "--cases", "--report-only"],
                              cwd=ROOT, capture_output=True, text=True, check=False)
    assert conflict.returncode != 0
