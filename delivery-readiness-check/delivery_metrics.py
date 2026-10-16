#!/usr/bin/env python3
"""Compute DORA-style change fail rate and lead time for changes from a deploy-history CSV.

Definitions follow DORA 2025 (State of AI-assisted Software Development, p. 13):
- Lead time for changes: time from commit to version control to deployed in production.
- Change fail rate: ratio of deployments that require immediate intervention
  (rollback or hotfix) following a deployment.

CSV columns (header required):
  deploy_id, commit_time, deploy_time, failed, ai_assisted (optional)
  times: ISO 8601 (e.g. 2026-09-01T10:00:00+00:00); failed: true/false/1/0/yes/no
Standard library only. Python 3.9+.
Usage: python3 delivery_metrics.py deploys.csv [--max-cfr 0.15] [--max-lead-hours 24]
Exit code 0 = pass, 1 = fail thresholds, 2 = bad input.
"""
import argparse, csv, statistics, sys
from datetime import datetime

TRUE = {"true", "1", "yes", "y"}
FALSE = {"false", "0", "no", "n", ""}

def parse_bool(v, row):
    s = (v or "").strip().lower()
    if s in TRUE: return True
    if s in FALSE: return False
    raise ValueError(f"row {row}: bad boolean {v!r}")

def parse_time(v, row, col):
    try:
        t = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
    except Exception:
        raise ValueError(f"row {row}: bad {col} {v!r}")
    if t.tzinfo is None:
        raise ValueError(f"row {row}: {col} has no timezone offset")
    return t

def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        need = {"deploy_id", "commit_time", "deploy_time", "failed"}
        missing = need - set(r.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        for i, d in enumerate(r, start=2):
            c = parse_time(d["commit_time"], i, "commit_time")
            p = parse_time(d["deploy_time"], i, "deploy_time")
            if p < c:
                raise ValueError(f"row {i}: deploy_time before commit_time")
            ai = d.get("ai_assisted")
            rows.append({"id": d["deploy_id"], "lead_h": (p - c).total_seconds() / 3600,
                         "failed": parse_bool(d["failed"], i),
                         "ai": None if ai is None or ai.strip() == "" else parse_bool(ai, i)})
    if not rows:
        raise ValueError("no deploy rows")
    return rows

def metrics(rows):
    leads = sorted(x["lead_h"] for x in rows)
    p90 = leads[min(len(leads) - 1, int(round(0.9 * (len(leads) - 1))))]
    return {"deploys": len(rows), "failed": sum(x["failed"] for x in rows),
            "change_fail_rate": sum(x["failed"] for x in rows) / len(rows),
            "lead_time_median_h": statistics.median(leads), "lead_time_p90_h": p90}

def fmt(name, m):
    return (f"{name:<12} deploys={m['deploys']:>3}  failed={m['failed']:>2}  "
            f"CFR={m['change_fail_rate']:.1%}  lead median={m['lead_time_median_h']:.1f}h  "
            f"p90={m['lead_time_p90_h']:.1f}h")

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv")
    ap.add_argument("--max-cfr", type=float, default=0.15, help="pass threshold, set your own (default 0.15)")
    ap.add_argument("--max-lead-hours", type=float, default=24.0, help="median lead time threshold (default 24)")
    a = ap.parse_args(argv)
    try:
        rows = load(a.csv)
    except (ValueError, OSError) as e:
        print(f"input error: {e}", file=sys.stderr); return 2
    m = metrics(rows)
    print(fmt("all", m))
    for flag, label in ((True, "ai_assisted"), (False, "not_ai")):
        sub = [x for x in rows if x["ai"] is flag]
        if sub: print(fmt(label, metrics(sub)))
    if len(rows) < 20:
        print(f"warning: only {len(rows)} deploys; treat the rates as indicative, not stable")
    ok_cfr = m["change_fail_rate"] <= a.max_cfr
    ok_lead = m["lead_time_median_h"] <= a.max_lead_hours
    print(f"check CFR <= {a.max_cfr:.0%}: {'PASS' if ok_cfr else 'FAIL'}")
    print(f"check median lead <= {a.max_lead_hours:g}h: {'PASS' if ok_lead else 'FAIL'}")
    return 0 if ok_cfr and ok_lead else 1

if __name__ == "__main__":
    sys.exit(main())
