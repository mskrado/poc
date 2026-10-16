import csv
from pathlib import Path
import pytest
from twoarm import arms, log, readout

REF = Path(__file__).resolve().parent.parent / "tasks/arm_a_greenfield/reference/server.py"


def test_arm_a_empty_fails_reference_passes(tmp_path):
    ws = arms.prepare("A", tmp_path / "a")
    assert arms.grade("A", ws)[0] == 0
    (ws / "server.py").write_text(REF.read_text())
    assert arms.grade("A", ws) == (12, 12)


def test_arm_b_seed_fails(tmp_path):
    ws = arms.prepare("B", tmp_path / "b")
    p, t = arms.grade("B", ws)
    assert t > 0 and p < t


def test_no_ai_rejects_tool(tmp_path):
    with pytest.raises(ValueError):
        log.start("A", "no_ai", tmp_path / "x", "me", "copilot", 0)


def test_run_logged_and_arms_never_blended(tmp_path):
    ws = tmp_path / "a"; res = tmp_path / "runs.csv"
    log.start("A", "ai", ws, "me", "tool", -20)
    (ws / "server.py").write_text(REF.read_text())
    row = log.finish(ws, -30, res)
    assert row["solved"] == 1 and row["wall_s"] >= 0
    rows = list(csv.DictReader(res.open()))
    s = readout.summarize(rows)
    assert s[0]["measured_pct"] is None  # no no-AI run yet -> no ratio invented
    assert "n/a" in readout.markdown(rows)
