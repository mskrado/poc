#!/usr/bin/env python3
"""How many of the 50 tickets route to a human at several thresholds.

Reads results/results.csv from the shipped run. Does not call a model.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.sweep import DEFAULT_THRESHOLDS, sweep_router  # noqa: E402


def main():
    path = ROOT / "results" / "results.csv"
    if not path.exists():
        print(f"missing {path}", file=sys.stderr)
        return 1
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    table = sweep_router(rows, DEFAULT_THRESHOLDS)
    if not table or table[0]["tickets"] != 50:
        print(f"expected 50 router rows, found {table[0]['tickets'] if table else 0}", file=sys.stderr)
        return 1
    print("Computed from the shipped run (results/results.csv, gate=router_gate). No model calls.")
    print("Score is P(chosen label), as stored (4 decimal places).")
    print()
    header = ("threshold", "to_human", "confident_human", "low_confidence_fallback", "small_model", "frontier")
    print("| " + " | ".join(header) + " |")
    print("| " + " | ".join("---" for _ in header) + " |")
    for row in table:
        cells = [
            f"{row['threshold']:.1f}",
            str(row["route_human"]),
            str(row["confident_human"]),
            str(row["low_confidence_fallback"]),
            str(row["route_small"]),
            str(row["route_frontier"]),
        ]
        print("| " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
