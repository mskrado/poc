"""Start/finish timing. One row per run in results/runs.csv. Nothing is estimated for you."""
from __future__ import annotations
import csv, json, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from . import arms, env

FIELDS = ["run_id", "arm", "condition", "who", "tool", "started_utc", "finished_utc", "wall_s",
          "forecast_pct", "felt_pct", "tests_passed", "tests_total", "solved", "python", "hardware", "notes"]
STATE = ".twoarm_run.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def start(arm: str, condition: str, workspace: Path, who: str, tool: str, forecast_pct: float) -> dict:
    """forecast_pct: before starting, how much AI changes completion time for this task (-30 = 30% faster)."""
    if condition not in ("ai", "no_ai"):
        raise ValueError("condition must be ai or no_ai")
    if condition == "no_ai" and tool:
        raise ValueError("no_ai runs take no tool")
    ws = arms.prepare(arm, workspace)
    st = {"run_id": uuid.uuid4().hex[:8], "arm": arm, "condition": condition, "who": who, "tool": tool,
          "forecast_pct": forecast_pct, "started_utc": _now(), "t0": time.monotonic()}
    (ws / STATE).write_text(json.dumps(st))
    return st


def finish(workspace: Path, felt_pct: float, results: Path, notes: str = "") -> dict:
    """felt_pct: after finishing, how much you feel AI changed (or would have changed) your time."""
    workspace = Path(workspace)
    st = json.loads((workspace / STATE).read_text())
    wall = time.monotonic() - st.pop("t0")
    passed, total = arms.grade(st["arm"], workspace)
    row = {**st, "finished_utc": _now(), "wall_s": round(wall, 1), "felt_pct": felt_pct,
           "tests_passed": passed, "tests_total": total, "solved": int(total > 0 and passed == total),
           "python": env.python_version(), "hardware": env.hardware(), "notes": notes}
    results = Path(results); results.parent.mkdir(parents=True, exist_ok=True)
    new = not results.exists()
    with results.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
    (workspace / STATE).unlink()
    return row
