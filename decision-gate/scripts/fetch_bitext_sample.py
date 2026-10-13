#!/usr/bin/env python3
"""Download the Bitext customer-support CSV and rebuild the 50-ticket sample.

The full file is large and is not committed. This writes data/bitext.csv
(gitignored) and, by default, data/sample_tickets.csv. --check compares that
sample to results/sample_tickets.csv from the shipped run.

Dataset: bitext/Bitext-customer-support-llm-chatbot-training-dataset
License: CDLA-Sharing-1.0
Revision and sha256: gate/data.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.data import (  # noqa: E402
    BITEXT_FILE,
    BITEXT_REV,
    BITEXT_SHA256,
    N_TICKETS,
    SEED,
    ensure_dataset,
    sample_tickets,
)

COLS = ["ticket_id", "row", "category", "intent", "instruction", "flags"]


def _show(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return resolved.name


def _records(df):
    return list(map(tuple, df[COLS].astype(str).itertuples(index=False, name=None)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "data" / "sample_tickets.csv"),
                    help="where to write the reproduced sample")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 unless the sample matches results/sample_tickets.csv")
    a = ap.parse_args()

    dest = ensure_dataset(ROOT / "data" / "bitext.csv")
    sample = sample_tickets(dest, n=N_TICKETS, seed=SEED)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out, index=False)
    print(f"bitext file {BITEXT_FILE}")
    print(f"revision {BITEXT_REV}")
    print(f"sha256 {BITEXT_SHA256}")
    print(f"wrote {_show(out)} ({len(sample)} tickets, seed {SEED})")

    if not a.check:
        return 0
    shipped_path = ROOT / "results" / "sample_tickets.csv"
    if not shipped_path.exists():
        print(f"missing {shipped_path}", file=sys.stderr)
        return 1
    import pandas as pd
    shipped = pd.read_csv(shipped_path)
    got, exp = _records(sample), _records(shipped)
    if got != exp:
        print("sample does not match results/sample_tickets.csv", file=sys.stderr)
        for i, (g, e) in enumerate(zip(got, exp)):
            if g != e:
                print(f"first mismatch at row {i}: got {g[:3]} expected {e[:3]}", file=sys.stderr)
                break
        if len(got) != len(exp):
            print(f"length got {len(got)} expected {len(exp)}", file=sys.stderr)
        return 1
    print(f"sample matches {shipped_path.name} ({len(got)} tickets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
